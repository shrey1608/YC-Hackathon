"""
Seed sweep: find a SimConfig seed where a scenario's three bias axes isolate
cleanly under the offline self-validating loop.

Clean isolation (mirrors tests/test_sim.py contract):
  * verdict == REVIEW
  * accent: >= 3 accents flagged, general_american NOT flagged, with WER evidence
  * name_origin: latino AND south_asian flagged
  * gender: nothing flagged (untouched control)

Usage:
  python scripts/seed_sweep.py hiring_phone_screen           # scan seeds 0..199
  python scripts/seed_sweep.py hiring_phone_screen 0 500     # custom range
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fairbench.battery import build_battery  # noqa: E402
from fairbench.core.integrity import audit_report, result_from_battery_row  # noqa: E402
from fairbench.sim.eval import SimConfig, simulate_battery  # noqa: E402

PER_CELL = 8


def _audit(scenario_id: str, seed: int) -> dict:
    cases = build_battery(per_cell=PER_CELL)
    rows = simulate_battery(cases, SimConfig(scenario_id=scenario_id, seed=seed, save_sessions=False))
    return audit_report([result_from_battery_row(r) for r in rows])


def _flagged(report: dict, attr: str) -> set[str]:
    return {g for g, s in report["fairness"][attr].items() if s["adverse_impact"]}


def is_clean(report: dict) -> bool:
    accent = _flagged(report, "accent")
    name = _flagged(report, "name_origin")
    gender = _flagged(report, "gender")
    asr = {a["group"] for a in report["asr_bias"]}
    return (
        report["verdict"].startswith("REVIEW")
        and "general_american" not in accent
        and len(accent) >= 3
        and bool(asr)
        and {"latino", "south_asian"} <= name
        and not ({"anglo", "east_asian"} & name)  # unpenalized origins stay clean
        and not gender
    )


def main() -> None:
    scenario_id = sys.argv[1] if len(sys.argv) > 1 else "hiring_phone_screen"
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    for seed in range(lo, hi):
        rep = _audit(scenario_id, seed)
        if is_clean(rep):
            accent = sorted(_flagged(rep, "accent"))
            name = sorted(_flagged(rep, "name_origin"))
            print(f"CLEAN seed={seed} | accent={accent} | name_origin={name} | "
                  f"agreement={rep['reliability']['agreement']}")
            return
    print(f"no clean seed in [{lo}, {hi}) for {scenario_id}")


if __name__ == "__main__":
    main()
