"""
Cekura test-framework client.

Maps a Cekura result into FairBench integrity rows. Cekura's accent testing runs
the same workflow across accent *personalities* and scores a "Transcription
Accuracy" metric per run — exactly the per-accent signal FairBench's integrity
engine consumes.

  GET https://api.cekura.ai/test_framework/v1/results/{id}/
  header: X-CEKURA-API-KEY
  -> runs{}: each {success, personality_name, evaluation.metrics[...]}
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

BASE_URL = "https://api.cekura.ai"

# Create/run endpoints are inferred from Cekura's llms-full.txt and verified on
# first live call; the read+map path (get_result/result_rows) is the proven one.
_AGENTS_PATH = "/test_framework/v1/aiagents/"
_PERSONALITIES_PATH = "/test_framework/v1/personalities/"
_SCENARIOS_PATH = "/test_framework/v1/scenarios/"
_RUN_PATH = "/test_framework/v1/scenarios/run_scenarios_pipecat_v2/"


def _first(d: dict, *keys: str) -> Any:
    """Return the first present, non-null value among keys (shape-tolerant)."""
    for k in keys:
        if isinstance(d, dict) and d.get(k) is not None:
            return d[k]
    return None


class CekuraClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        self.api_key = api_key or os.environ.get("CEKURA_API_KEY")
        self.base_url = base_url.rstrip("/")

    # --- low-level -------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("CEKURA_API_KEY not set")
        return {"X-CEKURA-API-KEY": self.api_key, "Content-Type": "application/json"}

    def _post(self, path: str, payload: dict) -> dict[str, Any]:
        resp = httpx.post(
            f"{self.base_url}{path}", headers=self._headers(), json=payload, timeout=90.0
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # --- read + map (proven) --------------------------------------------
    def get_result(self, result_id: str | int) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("CEKURA_API_KEY not set")
        resp = httpx.get(
            f"{self.base_url}/test_framework/v1/results/{result_id}/",
            headers={"X-CEKURA-API-KEY": self.api_key},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()

    def result_rows(self, result_id: str | int) -> list[dict]:
        """Fetch a result and map its runs to FairBench integrity rows."""
        return map_runs(self.get_result(result_id))

    def poll_result(
        self, result_id: str | int, *, interval: float = 5.0, timeout: float = 900.0
    ) -> dict[str, Any]:
        """Poll a result until it reaches a terminal status (or the timeout)."""
        terminal = {"completed", "complete", "done", "finished", "failed", "error"}
        deadline = time.time() + timeout
        while True:
            result = self.get_result(result_id)
            if str(result.get("status", "")).lower() in terminal:
                return result
            if time.time() > deadline:
                return result
            time.sleep(interval)

    # --- programmatic create + run (verify on first live call) -----------
    def create_agent(self, name: str, agent_url: str, provider: str = "pipecat", **extra) -> dict:
        return self._post(_AGENTS_PATH, {"name": name, "provider": provider, "agent_url": agent_url, **extra})

    def create_personality(self, name: str, *, accent: str | None = None, gender: str | None = None, **extra) -> dict:
        payload: dict[str, Any] = {"name": name, **extra}
        if accent:
            payload["accent"] = accent
        if gender:
            payload["gender"] = gender
        return self._post(_PERSONALITIES_PATH, payload)

    def create_scenario(self, name: str, *, prompt: str | None = None, **extra) -> dict:
        payload: dict[str, Any] = {"name": name, **extra}
        if prompt:
            payload["prompt"] = prompt
        return self._post(_SCENARIOS_PATH, payload)

    def start_run(self, agent_id, scenario_ids, personality_ids, **extra) -> dict:
        return self._post(
            _RUN_PATH,
            {
                "agent_id": agent_id,
                "scenario_ids": list(scenario_ids),
                "personality_ids": list(personality_ids),
                **extra,
            },
        )

    def run_accent_battery(
        self,
        *,
        agent_url: str,
        accents: list[str],
        scenario_name: str,
        scenario_prompt: str,
        genders: list[str] | None = None,
        agent_name: str = "FairBench voice agent",
    ) -> str:
        """Mirror the matched battery onto Cekura: one agent + one scenario +
        one accent personality per accent, then start a pipecat run.

        Returns the ``result_id`` to poll. Cekura must be able to reach
        ``agent_url`` (a public Pipecat Cloud / Twilio endpoint), so this is a
        deployed-agent path, not localhost.
        """
        agent = self.create_agent(agent_name, agent_url)
        agent_id = _first(agent, "id", "agent_id", "uuid")

        scenario = self.create_scenario(scenario_name, prompt=scenario_prompt)
        scenario_id = _first(scenario, "id", "scenario_id", "uuid")

        personality_ids: list[Any] = []
        for accent in accents:
            for gender in genders or [None]:
                label = accent if gender is None else f"{accent}-{gender}"
                p = self.create_personality(label, accent=accent, gender=gender)
                pid = _first(p, "id", "personality_id", "uuid")
                if pid is not None:
                    personality_ids.append(pid)

        run = self.start_run(agent_id, [scenario_id], personality_ids)
        result_id = _first(run, "result_id", "id", "result", "run_id")
        if result_id is None:
            raise RuntimeError(f"Cekura run started but no result_id in response: {run}")
        return str(result_id)


def _transcription_wer(metrics: list[dict]) -> float | None:
    """Derive a WER proxy from Cekura's Transcription Accuracy metric (if present)."""
    for m in metrics or []:
        if "transcription" in str(m.get("name", "")).lower():
            score = m.get("score")
            if score is None:
                return None
            score = float(score)
            acc = score / 100.0 if score > 1 else score
            return round(max(0.0, 1.0 - acc), 3)
    return None


def map_runs(result: dict) -> list[dict]:
    """Convert a Cekura result payload into integrity rows.

    Cekura accent testing sweeps personalities (accents), so personality_name maps
    to the accent group. expert_label is left None unless an expected outcome is
    present (Cekura's met-expected-outcome is the ground-truth pass).
    """
    runs = result.get("runs", {})
    items = runs.values() if isinstance(runs, dict) else runs
    rows: list[dict] = []
    for run in items:
        metrics = (run.get("evaluation") or {}).get("metrics", [])
        personality = run.get("personality_name") or "unknown"
        expected = run.get("expected_outcome") or {}
        expert = expected.get("score")
        rows.append(
            {
                "persona_id": str(run.get("id") or f"{personality}-{len(rows)}"),
                "group": {"accent": personality},
                "passed": bool(run.get("success")),
                "expert_label": (None if expert is None else bool(expert)),
                "asr_wer": _transcription_wer(metrics),
                "scenario": run.get("scenario_name"),
                "status": run.get("status"),
            }
        )
    return rows
