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


# Keyword evidence per criterion — the single source of truth shared by the
# grader and the offline simulator (fairbench/sim). Keep keywords lowercase.
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

        checks = KEYWORD_CHECKS

        for criterion in self.rubric.criteria:
            keywords = checks.get(criterion.id, [])
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
