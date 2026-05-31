"""Session grader — scores turns against rubric criteria."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fairbench.core.rubric import Rubric
from fairbench.core.scenario import Scenario


class CriterionScore(BaseModel):
    criterion_id: str
    score: float
    evidence: list[str] = Field(default_factory=list)


class SessionGrade(BaseModel):
    scenario_id: str
    session_id: str
    competency_scores: dict[str, float]
    overall: float
    passed: bool
    evidence: list[dict] = Field(default_factory=list)


# Fallback keyword evidence per criterion, used only when a rubric's Criterion
# does not carry its own ``keywords`` (the pluggable path). Pluggable scenarios
# define keywords in their rubric YAML; these cover the original two rubrics.
# Keep keywords lowercase.
KEYWORD_CHECKS: dict[str, list[str]] = {
    "verify_prescription": ["verify", "prescription", "check your rx"],
    "clarify_contraindications": ["food", "contraindication", "side effect", "clarify"],
    "empathy_and_clarity": ["understand", "happy to help", "let me explain"],
    "escalate_to_pharmacist": ["pharmacist", "escalate", "ask the pharmacist"],
    "sbar_situation": ["calling about", "patient in", "situation"],
    "sbar_background": ["history", "admitted", "background"],
    "sbar_assessment": ["assess", "concerned", "vitals", "bp", "fever"],
    "sbar_recommendation": ["recommend", "suggest", "need orders", "urgent"],
}


# Short, actionable coaching nudges per criterion for live (per-turn) feedback.
# Falls back to the criterion's display name when a criterion isn't listed.
COACHING_HINTS: dict[str, str] = {
    "verify_prescription": "Confirm the prescription/Rx details before you advise.",
    "clarify_contraindications": "Ask about food and other meds, and flag any interaction.",
    "empathy_and_clarity": "Acknowledge the patient and explain it in plain language.",
    "escalate_to_pharmacist": "Offer to bring in the pharmacist for the clinical question.",
    "sbar_situation": "State the situation: who the patient is and why you're calling.",
    "sbar_background": "Give the relevant background/history.",
    "sbar_assessment": "Share your assessment — vitals, what's concerning you.",
    "sbar_recommendation": "Make a clear recommendation or ask for specific orders.",
}


def live_feedback(grade: SessionGrade, rubric: Rubric) -> dict:
    """Turn a (cumulative) grade into immediate coaching for the live call.

    Buckets each rubric criterion as met / partial / unmet, then surfaces ONE
    next action — the highest-weight criterion not yet met — so the trainee gets
    a single, specific nudge after every turn instead of a wall of scores.
    """
    scores = grade.competency_scores
    met = [c for c, s in scores.items() if s >= 0.66]
    partial = [c for c, s in scores.items() if 0.34 <= s < 0.66]
    unmet = [c for c, s in scores.items() if s < 0.34]

    weight = {c.id: c.weight for c in rubric.criteria}
    name = {c.id: c.name for c in rubric.criteria}
    candidates = unmet or partial
    target = max(candidates, key=lambda c: weight.get(c, 1.0)) if candidates else None
    if target:
        hint = COACHING_HINTS.get(target) or (
            f"Work in: {name.get(target, target).replace('_', ' ')}."
        )
    else:
        hint = "Strong — every competency is on track. Wrap up cleanly."

    return {
        "overall": grade.overall,
        "passed": grade.passed,
        "scores": scores,
        "met": met,
        "partial": partial,
        "unmet": unmet,
        "target": target,
        "hint": hint,
        "criteria_names": name,
    }


class SessionGrader:
    """Scores trainee turns against the active rubric."""

    def __init__(self, scenario: Scenario, rubric: Rubric):
        self.scenario = scenario
        self.rubric = rubric

    def grade_transcript(self, session_id: str, turns: list[dict]) -> SessionGrade:
        """Grade a transcript. Each turn: {"role": "patient"|"trainee", "text": "..."}."""
        trainee_text = " ".join(
            t["text"].lower() for t in turns if t.get("role") == "trainee"
        )
        scores: dict[str, float] = {}
        evidence: list[dict] = []

        for criterion in self.rubric.criteria:
            # Prefer the rubric-carried keywords (data-driven, pluggable); fall
            # back to the module table for the original built-in rubrics.
            keywords = criterion.keywords or KEYWORD_CHECKS.get(criterion.id, [])
            hits = [kw for kw in keywords if kw in trainee_text]
            score = min(1.0, len(hits) / max(1, len(keywords) * 0.5)) if keywords else 0.5
            scores[criterion.id] = round(score, 2)
            if hits:
                evidence.append(
                    {
                        "criterion": criterion.id,
                        "matched": hits,
                    }
                )

        weights = {c.id: c.weight for c in self.rubric.criteria}
        total_w = sum(weights.values()) or 1.0
        overall = sum(scores[k] * weights.get(k, 1.0) for k in scores) / total_w
        passed = overall >= self.scenario.pass_overall

        return SessionGrade(
            scenario_id=self.scenario.id,
            session_id=session_id,
            competency_scores=scores,
            overall=round(overall, 2),
            passed=passed,
            evidence=evidence,
        )
