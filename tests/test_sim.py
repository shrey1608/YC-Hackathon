"""
Validation tests for the self-validating offline loop.

These assert that bias *emerges* from the real grader running over accent-degraded
transcripts and is correctly attributed by the integrity engine — not hard-coded.
"""

from pathlib import Path

from fairbench.battery import build_battery
from fairbench.core.grader import SessionGrader
from fairbench.core.integrity import audit_report, result_from_battery_row
from fairbench.core.scenario import load_scenario
from fairbench.sim.eval import SimConfig, simulate_battery
from fairbench.sim.transcripts import generate_transcript

ROOT = Path(__file__).resolve().parents[1]
PER_CELL = 8


def _audit(**kw) -> dict:
    cases = build_battery(per_cell=PER_CELL)
    rows = simulate_battery(cases, SimConfig(save_sessions=False, **kw))
    return audit_report([result_from_battery_row(r) for r in rows])


def _flagged(report: dict, attr: str) -> set[str]:
    return {g for g, s in report["fairness"][attr].items() if s["adverse_impact"]}


def _asr_groups(report: dict) -> set[str]:
    return {a["group"] for a in report["asr_bias"]}


# --- the validation matrix -------------------------------------------------


def test_clean_run_has_no_false_positives():
    """No injected bias -> PASS, perfect reliability, nothing flagged anywhere."""
    rep = _audit(asr_enabled=False, grader_name_bias_rate=0.0)
    assert rep["verdict"].startswith("PASS")
    assert rep["reliability"]["agreement"] == 1.0
    assert not _flagged(rep, "accent")
    assert not _flagged(rep, "gender")
    assert not _flagged(rep, "name_origin")
    assert not _asr_groups(rep)


def test_default_run_flags_accent_and_name_not_gender():
    rep = _audit()
    assert rep["verdict"].startswith("REVIEW")
    # general_american is the reference and must not be flagged
    assert "general_american" not in _flagged(rep, "accent")
    assert len(_flagged(rep, "accent")) >= 3
    assert {"latino", "south_asian"} <= _flagged(rep, "name_origin")
    # gender is an untouched control — no false positive
    assert not _flagged(rep, "gender")
    # the grader's bias shows up as false-fails of competent performances
    assert rep["reliability"]["agreement"] < 1.0
    assert rep["reliability"]["false_fail_rate"] > 0.0


def test_asr_bias_attributed_to_accent_with_wer_evidence():
    """Accent bias only -> accent flagged WITH a matching WER gap."""
    rep = _audit(grader_name_bias_rate=0.0)
    assert len(_flagged(rep, "accent")) >= 3
    assert _asr_groups(rep)  # WER evidence present
    assert not _flagged(rep, "gender")
    assert not _flagged(rep, "name_origin")


def test_grader_bias_attributed_to_name_without_wer_evidence():
    """Name bias only -> name flagged but NO WER gap: it's the grader, not the STT."""
    rep = _audit(asr_enabled=False)
    assert {"latino", "south_asian"} <= _flagged(rep, "name_origin")
    assert not _asr_groups(rep)          # the key attribution claim
    assert not _flagged(rep, "accent")
    assert not _flagged(rep, "gender")


def test_simulation_is_deterministic():
    a = _audit()
    b = _audit()
    assert a["verdict"] == b["verdict"]
    for attr in ("accent", "gender", "name_origin"):
        assert _flagged(a, attr) == _flagged(b, attr)


# --- the grader is actually accurate on clean transcripts ------------------


def _grader():
    scenario = load_scenario(ROOT / "data/synthetic/scenarios/pharmacy_tech_metformin.yaml")
    rubric = scenario.load_rubric(ROOT / "data/synthetic/rubrics")
    return SessionGrader(scenario, rubric), rubric, scenario


def test_clean_good_passes_unsafe_and_borderline_fail():
    grader, rubric, scenario = _grader()
    opening = scenario.persona.opening_line
    outcomes = {}
    for behavior in ("good_tech", "unsafe_tech", "borderline_tech"):
        turns = generate_transcript(behavior, rubric, opening)
        outcomes[behavior] = grader.grade_transcript(behavior, turns).passed
    assert outcomes["good_tech"] is True
    assert outcomes["unsafe_tech"] is False
    assert outcomes["borderline_tech"] is False
