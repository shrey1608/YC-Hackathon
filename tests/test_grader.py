from pathlib import Path

from fairbench.core.grader import SessionGrader
from fairbench.core.scenario import load_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_pharmacy_grade_pass():
    scenario = load_scenario(ROOT / "data/synthetic/scenarios/pharmacy_tech_metformin.yaml")
    rubric = scenario.load_rubric(ROOT / "data/synthetic/rubrics")
    grader = SessionGrader(scenario, rubric)
    turns = [
        {"role": "patient", "text": "metformin with food?"},
        {
            "role": "trainee",
            "text": (
                "I'll verify your prescription. Metformin is often taken with food "
                "to reduce upset — let me explain, and I'll get the pharmacist to clarify directions."
            ),
        },
    ]
    grade = grader.grade_transcript("test-1", turns)
    assert grade.passed
    assert grade.overall >= 0.75
    assert "escalate_to_pharmacist" in grade.competency_scores
