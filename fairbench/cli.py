"""CLI: battery build, integrity audit, offline self-validating demo, rubric."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fairbench.battery import build_battery
from fairbench.core.integrity import (
    Result,
    audit_report,
    demo_results,
    result_from_battery_row,
    save_audit,
)
from fairbench.core.rubrics_config import active_rubric


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_battery_results(path: Path) -> list[Result]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("results", [])
    return [result_from_battery_row(r) if isinstance(r, dict) else r for r in rows]


def cmd_battery(args: argparse.Namespace) -> None:
    cases = build_battery(slim=args.slim)
    print(f"battery: {len(cases)} cases (slim={args.slim})")
    if args.output:
        out = _project_root() / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(cases, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    if args.print_example:
        print("example:", cases[0])


def _build_report(args: argparse.Namespace) -> dict:
    """Resolve which results feed the audit: external file, demo, live provider, or sim."""
    if args.results:
        results = _load_battery_results(_project_root() / args.results)
        return audit_report(results)
    if args.demo:
        return audit_report(demo_results())
    if getattr(args, "live", False):
        # route through the configured eval provider (Cekura when keyed, else sim)
        from fairbench.adapters.pipeline import make_eval

        rows = make_eval().run_battery(args.agent_url, build_battery(slim=True))
        return audit_report([result_from_battery_row(r) for r in rows])
    # default: the self-validating offline loop
    from fairbench.sim.eval import SimConfig, run_sim_audit

    cfg = SimConfig(seed=args.seed, scenario_id=args.scenario)
    return run_sim_audit(cfg, per_cell=args.per_cell)


def _print_flags(report: dict) -> None:
    for attr, groups in report.get("fairness", {}).items():
        flagged = [g for g, s in groups.items() if s.get("adverse_impact")]
        if flagged:
            print(f"  adverse impact ({attr}): {', '.join(sorted(flagged))}")
    asr = [a["group"] for a in report.get("asr_bias", [])]
    if asr:
        print(f"  ASR-bias accents: {', '.join(asr)}")


def cmd_audit(args: argparse.Namespace) -> None:
    report = _build_report(args)
    out = _project_root() / args.output
    save_audit(report, out)
    rel = report.get("reliability", {})
    print(f"FairBench audit written to {out}")
    print(f"Verdict: {report['verdict']}")
    if rel.get("agreement") is not None:
        print(f"Grader agreement vs experts: {rel['agreement']} (false-fail {rel['false_fail_rate']})")
    _print_flags(report)


def cmd_demo(args: argparse.Namespace) -> None:
    """One command: run the offline self-validating loop and write the audit + sessions."""
    from fairbench.sim.eval import SimConfig, run_sim_audit

    print("FairBench demo: matched battery -> synthetic transcripts -> accent ASR")
    print("degradation -> REAL grader -> integrity audit. Synthetic data only.\n")
    cfg = SimConfig(seed=args.seed, scenario_id=args.scenario)
    report = run_sim_audit(cfg, per_cell=args.per_cell)
    out = _project_root() / args.output
    save_audit(report, out)
    rel = report["reliability"]
    print(f"Performances: {report['n_performances']} "
          f"(qualified cohort {report['fairness_cohort_n']})")
    print(f"Verdict: {report['verdict']}")
    print(f"Grader agreement vs experts: {rel['agreement']} "
          f"| false-fail {rel['false_fail_rate']}")
    _print_flags(report)
    print(f"\nReport: {out}  (and {out.with_suffix('.json')})")
    print("Dashboard: cd dashboard && npm install && npm run dev")


def _cmd_rubric() -> None:
    key, block = active_rubric()
    print(f"active: {key}")
    print(f"display: {block.get('display_name')}")
    print(f"metrics: {[m['id'] for m in block.get('metrics', [])]}")


def _add_audit_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--demo", action="store_true", help="Planted-bias self-test (4 hardcoded rows)")
    p.add_argument("--sim", action="store_true", help="Offline self-validating loop (default)")
    p.add_argument("--results", default=None, help="JSON battery results from Cekura/harness")
    p.add_argument("--live", action="store_true", help="Route through the eval provider (Cekura if keyed)")
    p.add_argument("--agent-url", default="http://localhost:7860", dest="agent_url")
    p.add_argument("--scenario", default="pharmacy_tech_metformin", help="Scenario id for the sim")
    p.add_argument("--seed", type=int, default=11, help="Sim RNG seed")
    p.add_argument("--per-cell", type=int, default=8, dest="per_cell", help="Sim repeats per cell")
    p.add_argument("--output", default="reports/audit.md")


def main() -> None:
    parser = argparse.ArgumentParser(prog="fairbench", description="FairBench CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bat = sub.add_parser("battery", help="Build matched bias battery from personas.yaml")
    p_bat.add_argument("--slim", action="store_true", help="~30 cases for live demo")
    p_bat.add_argument("--output", default=None, help="Write JSON e.g. data/synthetic/battery_slim.json")
    p_bat.add_argument("--print-example", action="store_true")
    p_bat.set_defaults(func=cmd_battery)

    p_aud = sub.add_parser("audit", help="Run integrity audit (offline sim by default)")
    _add_audit_args(p_aud)
    p_aud.set_defaults(func=cmd_audit)

    p_demo = sub.add_parser("demo", help="One-command offline self-validating demo")
    p_demo.add_argument("--scenario", default="pharmacy_tech_metformin")
    p_demo.add_argument("--seed", type=int, default=11)
    p_demo.add_argument("--per-cell", type=int, default=8, dest="per_cell")
    p_demo.add_argument("--output", default="reports/audit.md")
    p_demo.set_defaults(func=cmd_demo)

    p_rub = sub.add_parser("rubric", help="Show active rubric from rubrics.yaml")
    p_rub.set_defaults(func=lambda a: _cmd_rubric())

    args = parser.parse_args()
    args.func(args)


def audit_main() -> None:
    """Legacy entry point: fairbench-audit -> audit (offline sim) by default."""
    import sys

    if len(sys.argv) <= 1:
        sys.argv = [sys.argv[0], "audit"]
    elif sys.argv[1] not in ("audit", "battery", "rubric", "demo"):
        sys.argv.insert(1, "audit")
    main()


if __name__ == "__main__":
    main()
