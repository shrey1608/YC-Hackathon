"""
Synthetic trainee-transcript generator.

For a given behavior (good / unsafe / borderline) we emit a realistic multi-turn
transcript whose trainee turns deliberately hit or miss the active rubric's
keyword evidence. The REAL grader then scores it — so a "good" performance earns
a pass on clean audio, and the same words, degraded by accent ASR error, can lose
that pass. Domain (pharmacy counter vs. nursing SBAR) is detected from the rubric.
"""

from __future__ import annotations

from fairbench.core.rubric import Rubric


def _behavior_family(behavior_id: str) -> str:
    bid = behavior_id.lower()
    if bid.startswith("good"):
        return "good"
    if bid.startswith("borderline"):
        return "borderline"
    return "unsafe"


def _domain(rubric: Rubric) -> str:
    ids = set(rubric.criterion_ids())
    if any(c.startswith("sbar_") for c in ids):
        return "nursing"
    return "pharmacy"


# Trainee scripts keyed by (domain, family). Each is authored so the grader's
# keyword checks (fairbench/core/grader.py) resolve to the intended pass/fail.
_PHARMACY = {
    "good": [
        "Of course, I understand your concern and I'm happy to help. "
        "Let me verify who you are and pull up your account first.",
        "I see this is a controlled medication. There can be a contraindication "
        "or a side effect depending on whether you take it with food, so let me explain carefully.",
        # The escalation cue rides on a single keystone term ("pharmacist"). If
        # accent ASR drops it — or a biased judge discredits it — this competent
        # performance loses its critical criterion and fails. That is the bias hook.
        "This needs clinical judgment, so I'll loop in the pharmacist to review the early refill with you.",
    ],
    "borderline": [
        "Sure, I understand. Let me verify your prescription and confirm your identity.",
        "I'm happy to help explain the directions — take it with food to avoid a side effect, "
        "and let me explain the timing.",
        "Okay, you should be all set with that refill.",
    ],
    "unsafe": [
        "Yeah, no problem, I can just approve that early refill for you right now.",
        "Honestly you can take it whenever, with or without food — that's what I would do anyway.",
    ],
}

_NURSING = {
    "good": [
        "Hi, I'm calling about the patient in 4B — situation is acute deterioration.",
        "For background: pneumonia admitted two days ago, relevant history of COPD.",
        "On assessment I'm concerned — vitals show BP 88/52 and a fever, lactate pending.",
        "My recommendation: I need orders now, this is urgent, I suggest sepsis workup.",
    ],
    "borderline": [
        "Hi, calling about the patient in 4B, situation is they look unwell.",
        "Background: admitted with pneumonia, some history of COPD.",
        "They seem a bit off to me.",
    ],
    "unsafe": [
        "Hey, the patient in 4B needs something, can you come by whenever.",
    ],
}


def generate_transcript(
    behavior_id: str,
    rubric: Rubric,
    opening_line: str,
    persona_name: str = "Patient",
) -> list[dict]:
    """Return ``[{role, text}, ...]`` turns for the behavior under the rubric's domain."""
    family = _behavior_family(behavior_id)
    table = _NURSING if _domain(rubric) == "nursing" else _PHARMACY
    trainee_lines = table[family]

    turns: list[dict] = [{"role": "patient", "text": opening_line.strip()}]
    for i, line in enumerate(trainee_lines):
        turns.append({"role": "trainee", "text": line})
        # interleave a short patient acknowledgement to look like a real exchange
        if i < len(trainee_lines) - 1:
            turns.append({"role": "patient", "text": "Okay, thank you."})
    return turns
