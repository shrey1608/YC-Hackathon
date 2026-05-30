"""
FairBench voice/text bot entry.

  FAIRBENCH_TRANSPORT=text   -> offline multi-turn text demo (no keys needed)
  otherwise                  -> live Pipecat voice pipeline (needs [bot] + keys)

The text demo plays a scripted trainee performance (selectable via
FAIRBENCH_BEHAVIOR) against a patient voiced by Nemotron when a live endpoint is
configured, then grades and saves the session — the same path the audit consumes.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from fairbench.config import load_config
from fairbench.core.grader import SessionGrader
from fairbench.core.scenario import load_scenario
from fairbench.session import save_session


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_active_scenario():
    cfg = load_config()
    scenario_id = os.environ.get("FAIRBENCH_SCENARIO", "pharmacy_tech_metformin")
    path = _project_root() / "data" / "synthetic" / "scenarios" / f"{scenario_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    scenario = load_scenario(path)
    rubric = scenario.load_rubric(_project_root() / cfg.data.rubrics_dir)
    return scenario, rubric, cfg


async def _patient_turn(llm, scenario, turns: list[dict], fallback: str) -> str:
    """Live patient reply via Nemotron when an endpoint is set, else the fallback."""
    if not getattr(llm, "endpoint", ""):
        return fallback
    messages = [{"role": "system", "content": scenario.system_prompt}]
    for t in turns:
        role = "user" if t["role"] == "trainee" else "assistant"
        messages.append({"role": role, "content": t["text"]})
    try:
        return (await llm.complete(messages)).strip() or fallback
    except Exception:  # noqa: BLE001 - any transport error -> stay offline
        return fallback


async def run_text_demo() -> None:
    """Offline-capable multi-turn conversation, graded against the active rubric."""
    from fairbench.adapters.factory import create_llm
    from fairbench.sim.transcripts import generate_transcript

    scenario, rubric, cfg = load_active_scenario()
    llm = create_llm(cfg)
    behavior = os.environ.get("FAIRBENCH_BEHAVIOR", "good_tech")

    scripted = generate_transcript(behavior, rubric, scenario.persona.opening_line)
    print(f"\n=== FairBench | {scenario.title} | behavior={behavior} ===\n")

    turns: list[dict] = []
    for turn in scripted:
        if turn["role"] == "patient":
            text = await _patient_turn(llm, scenario, turns, turn["text"])
            print(f"Patient: {text}\n")
        else:
            text = turn["text"]
            print(f"Trainee: {text}\n")
        turns.append({"role": turn["role"], "text": text})

    sid = save_session(scenario.id, turns, metadata={"behavior": behavior, "source": "text"})
    grade = SessionGrader(scenario, rubric).grade_transcript(sid, turns)
    print(f"Session: {sid}")
    print(f"Overall: {grade.overall} | Pass: {grade.passed}")
    print(f"Scores: {grade.competency_scores}\n")


def run_pipecat() -> None:
    """Full voice pipeline — requires pipecat-ai and sponsor credentials."""
    try:
        import pipecat  # noqa: F401
    except ImportError:
        print(
            'Pipecat not installed. Run: pip install -e ".[bot]" and pipecat-ai[gradium].\n'
            "Falling back to text demo.\n",
            file=sys.stderr,
        )
        asyncio.run(run_text_demo())
        return

    if not os.environ.get("GRADIUM_API_KEY"):
        print("GRADIUM_API_KEY not set — falling back to text demo.\n", file=sys.stderr)
        asyncio.run(run_text_demo())
        return

    from fairbench.bot.pipeline import run_voice_bot

    scenario, rubric, _cfg = load_active_scenario()
    print(f"=== FairBench live voice | {scenario.title} ===")
    asyncio.run(run_voice_bot(scenario, rubric))


def main() -> None:
    transport = os.environ.get("FAIRBENCH_TRANSPORT", "").lower()
    if transport == "text" or "--text" in sys.argv:
        asyncio.run(run_text_demo())
    else:
        run_pipecat()


if __name__ == "__main__":
    main()
