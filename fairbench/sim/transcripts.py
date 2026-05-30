"""
Synthetic trainee-transcript generator.

For a given behavior (good / unsafe / borderline) we emit a realistic multi-turn
transcript whose trainee turns deliberately hit or miss the active rubric's
keyword evidence. The REAL grader then scores it — so a "good" performance earns
a pass on clean audio, and the same words, degraded by accent ASR error, can lose
that pass. The per-behavior scripts are carried by the scenario YAML
(``scenario.sim_scripts``), so adding a scenario is data-only.
"""

from __future__ import annotations

from fairbench.core.scenario import Scenario


def _behavior_family(behavior_id: str) -> str:
    bid = behavior_id.lower()
    if bid.startswith("good"):
        return "good"
    if bid.startswith("borderline"):
        return "borderline"
    return "unsafe"


def generate_transcript(
    behavior_id: str,
    scenario: Scenario,
    persona_name: str = "Patient",
) -> list[dict]:
    """Return ``[{role, text}, ...]`` turns for the behavior under the scenario.

    Trainee lines come from ``scenario.sim_scripts[family]`` (family is
    good/borderline/unsafe). The opening patient line is the scenario persona's.
    """
    family = _behavior_family(behavior_id)
    trainee_lines = scenario.sim_scripts.get(family, [])
    if not trainee_lines:
        raise ValueError(
            f"scenario '{scenario.id}' has no sim_scripts for behavior family "
            f"'{family}'. Add sim_scripts.{family} to the scenario YAML."
        )

    turns: list[dict] = [{"role": "patient", "text": scenario.persona.opening_line.strip()}]
    for i, line in enumerate(trainee_lines):
        turns.append({"role": "trainee", "text": line})
        # interleave a short patient acknowledgement to look like a real exchange
        if i < len(trainee_lines) - 1:
            turns.append({"role": "patient", "text": "Okay, thank you."})
    return turns
