"""
SimulatedEval — the self-validating offline loop.

Runs the matched bias battery with NO external services:
  battery persona -> synthetic transcript -> accent ASR degradation -> REAL grader
  -> pass/fail + realized WER -> integrity audit.

Because the grader is real and the degradation is accent-correlated, adverse impact
and reliability loss emerge from the pipeline instead of being hard-coded. A second,
clearly-labelled knob (``grader_name_bias_rate``) simulates a biased LLM judge that
penalizes certain name origins, so the audit can attribute ASR bias (accent) and
grader bias (name_origin) to different mechanisms — while leaving gender clean to
show the engine does not cry wolf.
"""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass
from pathlib import Path

from fairbench.config import load_config
from fairbench.core.grader import KEYWORD_CHECKS, SessionGrader
from fairbench.core.rubric import Rubric
from fairbench.core.scenario import Scenario, load_scenario
from fairbench.sim.asr import accent_wer, degrade
from fairbench.sim.transcripts import generate_transcript


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# Two independent single-token evidence keystones in the "good" script
# (see sim/transcripts.py). ASR error attacks the escalation cue; a biased judge
# discredits the identity-verification cue. Separating them keeps the accent and
# name_origin signals from interfering.
ASR_KEYSTONE = "pharmacist"
NAME_KEYSTONE = "verify"


# Battery repeats per demographic cell for the offline audit. High enough that
# impact-ratio statistics are stable; the whole battery still simulates in well
# under a second. (Live calls use the small slim battery instead.)
DEFAULT_SIM_PER_CELL = 8


@dataclass
class SimConfig:
    scenario_id: str = "pharmacy_tech_metformin"
    seed: int = 11  # locked demo fixture: clean isolation across all three axes
    # Probability a *biased judge* discredits the escalation evidence for a
    # penalized name origin — a grader-bias mechanism distinct from ASR. Flows
    # through the real grader so it surfaces as name_origin adverse impact with
    # no accompanying WER gap.
    grader_name_bias_rate: float = 0.30
    biased_name_origins: tuple[str, ...] = ("latino", "south_asian")
    asr_enabled: bool = True
    save_sessions: bool = True


def _load_scenario_rubric(scenario_id: str) -> tuple[Scenario, Rubric]:
    cfg = load_config()
    root = _project_root()
    scenario = load_scenario(root / "data" / "synthetic" / "scenarios" / f"{scenario_id}.yaml")
    rubric = scenario.load_rubric(root / cfg.data.rubrics_dir)
    return scenario, rubric


def _rubric_keywords(rubric: Rubric) -> set[str]:
    kws: set[str] = set()
    for crit in rubric.criterion_ids():
        for kw in KEYWORD_CHECKS.get(crit, []):
            kws.update(kw.split())
    return kws


def _degrade_turns(
    turns: list[dict], wer: float, rng: random.Random, keywords: set[str]
) -> tuple[list[dict], float]:
    """Degrade trainee turns only; return new turns and the realized WER."""
    out: list[dict] = []
    total_err = 0.0
    total_turns = 0
    for t in turns:
        if t.get("role") != "trainee" or wer <= 0:
            out.append(t)
            continue
        degraded, realized = degrade(t["text"], wer, rng, keywords)
        out.append({"role": "trainee", "text": degraded})
        total_err += realized
        total_turns += 1
    avg = round(total_err / total_turns, 3) if total_turns else 0.0
    return out, avg


def _strip_keyword(turns: list[dict], keyword: str) -> list[dict]:
    """Remove a keystone term from trainee turns (a biased judge discrediting it)."""
    out: list[dict] = []
    for t in turns:
        if t.get("role") == "trainee":
            kept = [w for w in t["text"].split() if keyword not in w.lower()]
            out.append({"role": "trainee", "text": " ".join(kept)})
        else:
            out.append(t)
    return out


def simulate_battery(cases: list[dict], config: SimConfig | None = None) -> list[dict]:
    """Run the whole battery offline and return integrity-ready result rows."""
    config = config or SimConfig()
    scenario, rubric = _load_scenario_rubric(config.scenario_id)
    grader = SessionGrader(scenario, rubric)
    keywords = _rubric_keywords(rubric)
    opening = scenario.persona.opening_line

    rows: list[dict] = []
    saved_accents: set[str] = set()
    for case in cases:
        group = case.get("group", {})
        accent = group.get("accent")
        name_origin = group.get("name_origin", "unknown")
        behavior = case["behavior"]

        # Seed only on the attributes the bias model actually depends on
        # (behavior, accent, name_origin, rep). Gender is excluded, so matched
        # male/female personas get identical treatment and gender stays a clean
        # negative control — demonstrating the audit flags only where bias exists.
        rep = case["persona_id"].rsplit("__", 1)[-1]
        seed_key = f"{behavior}|{accent}|{name_origin}|{rep}"
        seed = (zlib.crc32(seed_key.encode()) ^ config.seed) & 0xFFFFFFFF
        rng = random.Random(seed)

        clean_turns = generate_transcript(behavior, rubric, opening, persona_name=name_origin)
        wer = accent_wer(accent) if config.asr_enabled else 0.0
        graded_turns, realized_wer = _degrade_turns(clean_turns, wer, rng, keywords)

        # Biased-judge mechanism: discredit the escalation evidence for some
        # penalized-origin personas. Adds no WER, so it shows up as name_origin
        # adverse impact only — never as an ASR flag.
        judge_biased = (
            name_origin in config.biased_name_origins
            and rng.random() < config.grader_name_bias_rate
        )
        if judge_biased:
            graded_turns = _strip_keyword(graded_turns, NAME_KEYSTONE)

        grade = grader.grade_transcript(case["persona_id"], graded_turns)

        rows.append(
            {
                "persona_id": case["persona_id"],
                "group": group,
                "passed": grade.passed,
                "expert_label": case.get("expert_label"),
                "asr_wer": realized_wer if config.asr_enabled else None,
                "overall": grade.overall,
                "behavior": behavior,
                "judge_biased": judge_biased,
                "status": "simulated",
            }
        )

        # Save one good-behavior transcript per accent: the same competent
        # performance, shown passing or failing across accents, for the dashboard.
        if (
            config.save_sessions
            and behavior.startswith("good")
            and accent not in saved_accents
        ):
            saved_accents.add(accent)
            _save_session(
                scenario.id, case, graded_turns, grade.passed, realized_wer, grade.overall
            )

    return rows


def _save_session(
    scenario_id: str,
    case: dict,
    turns: list[dict],
    passed: bool,
    wer: float,
    overall: float,
) -> None:
    from fairbench.session import save_session

    save_session(
        scenario_id,
        turns,
        metadata={
            "group": case.get("group", {}),
            "behavior": case["behavior"],
            "expert_label": case.get("expert_label"),
            "passed": passed,
            "asr_wer": wer,
            "overall": overall,
            "source": "simulated",
        },
        session_id=f"syn-sim-{case['persona_id']}",
    )


class SimulatedEval:
    """EvalProvider that runs the battery fully offline via simulate_battery()."""

    def __init__(self, config: SimConfig | None = None):
        self.config = config or SimConfig()

    def run_battery(self, agent_url: str, personas: list[dict]) -> list[dict]:
        return simulate_battery(personas, self.config)


def run_sim_audit(
    config: SimConfig | None = None,
    per_cell: int = DEFAULT_SIM_PER_CELL,
) -> dict:
    """Build the full matched battery, simulate it offline, and return the audit report."""
    from fairbench.battery import build_battery
    from fairbench.core.integrity import audit_report, result_from_battery_row

    cases = build_battery(per_cell=per_cell)
    rows = simulate_battery(cases, config)
    results = [result_from_battery_row(r) for r in rows]
    return audit_report(results)
