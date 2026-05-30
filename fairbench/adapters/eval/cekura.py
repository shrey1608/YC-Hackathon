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
from typing import Any

import httpx

BASE_URL = "https://api.cekura.ai"


class CekuraClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        self.api_key = api_key or os.environ.get("CEKURA_API_KEY")
        self.base_url = base_url.rstrip("/")

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
