"""
FairBench assessment-integrity engine.

Given battery results (transcripts + grader pass/fail + demographic tags), produces:
  - adverse-impact ratios per attribute (EEOC 4/5ths rule)
  - reliability vs. expert labels (agreement, false-pass, false-fail)
  - ASR-bias flags (accents transcribed worse -> hidden adverse impact)
  - audit-ready report with PASS / REVIEW verdict
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

PASS_THRESHOLD = 0.80


@dataclass
class Result:
    persona_id: str
    group: dict
    passed: bool
    expert_label: bool | None = None
    asr_wer: float | None = None


def impact_ratios(results: list[Result], attribute: str) -> dict:
    """Pass rate per group / top group's pass rate. < 0.80 flags adverse impact."""
    counts = defaultdict(lambda: [0, 0])
    for r in results:
        g = r.group.get(attribute, "unknown")
        counts[g][1] += 1
        counts[g][0] += int(r.passed)
    rates = {g: (p / t if t else 0.0) for g, (p, t) in counts.items()}
    top = max(rates.values()) if rates else 0.0
    return {
        g: {
            "pass_rate": round(rate, 3),
            "impact_ratio": round(rate / top, 3) if top else None,
            "adverse_impact": (top > 0 and rate / top < PASS_THRESHOLD),
            "n": counts[g][1],
        }
        for g, rate in rates.items()
    }


def reliability(results: list[Result]) -> dict:
    """How well your grader agrees with expert labels (on the labeled subset)."""
    labeled = [r for r in results if r.expert_label is not None]
    if not labeled:
        return {"n": 0, "agreement": None}
    n = len(labeled)
    agree = sum(r.passed == r.expert_label for r in labeled)
    false_pass = sum(r.passed and not r.expert_label for r in labeled)
    false_fail = sum((not r.passed) and r.expert_label for r in labeled)
    return {
        "n": n,
        "agreement": round(agree / n, 3),
        "false_pass_rate": round(false_pass / n, 3),
        "false_fail_rate": round(false_fail / n, 3),
    }


def asr_bias_flags(
    results: list[Result],
    attribute: str = "accent",
    wer_gap: float = 0.10,
) -> list[dict]:
    """Flag groups whose speech is transcribed worse than the best group."""
    by_group: dict[str, list[float]] = defaultdict(list)
    for r in results:
        if r.asr_wer is not None:
            by_group[r.group.get(attribute, "unknown")].append(r.asr_wer)
    avg = {g: sum(v) / len(v) for g, v in by_group.items() if v}
    if not avg:
        return []
    best = min(avg.values())
    return [
        {
            "group": g,
            "avg_wer": round(w, 3),
            "gap_vs_best": round(w - best, 3),
        }
        for g, w in sorted(avg.items(), key=lambda kv: -kv[1])
        if (w - best) > wer_gap
    ]


def audit_report(
    results: list[Result],
    attributes: tuple[str, ...] = ("accent", "gender", "name_origin"),
    fairness_cohort: str = "qualified",
) -> dict:
    """Single artifact for stage / compliance export.

    fairness_cohort="qualified" measures adverse impact only over performances
    experts label as a pass (equal-opportunity / true-positive-rate parity) — the
    matched-battery comparison of identical competent performance across groups.
    "all" uses every performance (classic selection-rate 4/5ths). Reliability and
    ASR-bias always span all performances. Falls back to all if no labels exist.
    """
    if fairness_cohort == "qualified":
        cohort = [r for r in results if r.expert_label is True] or results
    else:
        cohort = results

    fairness = {a: impact_ratios(cohort, a) for a in attributes}
    asr = asr_bias_flags(results)
    flagged = (
        any(grp["adverse_impact"] for a in attributes for grp in fairness[a].values())
        or bool(asr)
    )
    return {
        "n_performances": len(results),
        "fairness_cohort": fairness_cohort,
        "fairness_cohort_n": len(cohort),
        "reliability": reliability(results),
        "fairness": fairness,
        "asr_bias": asr,
        "verdict": "REVIEW - bias flagged" if flagged else "PASS - no adverse impact detected",
    }


def audit_to_markdown(report: dict) -> str:
    """Render audit_report dict for dashboard / fairbench-audit CLI."""
    lines = [
        "# FairBench Integrity Audit",
        "",
        f"Performances: {report['n_performances']} | "
        f"Fairness cohort ({report.get('fairness_cohort', 'all')}): "
        f"{report.get('fairness_cohort_n', report['n_performances'])} | Synthetic only: True",
        "",
        f"## Verdict: {report['verdict']}",
        "",
    ]

    rel = report.get("reliability", {})
    if rel.get("n"):
        lines.extend(
            [
                "## Grader reliability",
                "",
                f"n = {rel['n']} | agreement = {rel.get('agreement')} | "
                f"false_pass = {rel.get('false_pass_rate')} | false_fail = {rel.get('false_fail_rate')}",
                "",
            ]
        )

    for attr, groups in report.get("fairness", {}).items():
        lines.append(f"## Fairness — {attr}")
        lines.append("")
        lines.append("| Group | Pass rate | Impact ratio | N | Flag |")
        lines.append("|-------|-----------|--------------|---|------|")
        for g, stats in sorted(groups.items()):
            flag = "YES" if stats.get("adverse_impact") else ""
            ir = stats.get("impact_ratio")
            ir_s = f"{ir:.3f}" if ir is not None else "-"
            lines.append(
                f"| {g} | {stats['pass_rate']:.1%} | {ir_s} | {stats['n']} | {flag} |"
            )
        lines.append("")

    asr = report.get("asr_bias", [])
    if asr:
        lines.extend(["## ASR bias", ""])
        for row in asr:
            lines.append(
                f"- {row['group']}: avg WER {row['avg_wer']}, gap vs best {row['gap_vs_best']}"
            )
        lines.append("")

    return "\n".join(lines)


def save_audit(report: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(audit_to_markdown(report), encoding="utf-8")
    path.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def demo_results() -> list[Result]:
    """Planted bias self-test — same good behavior passes anglo male, fails spanish female."""
    return [
        Result(
            "good__anglo_m",
            {"accent": "general_american", "gender": "male", "name_origin": "anglo"},
            passed=True,
            expert_label=True,
            asr_wer=0.04,
        ),
        Result(
            "good__spanish_f",
            {"accent": "spanish_accented", "gender": "female", "name_origin": "latino"},
            passed=False,
            expert_label=True,
            asr_wer=0.19,
        ),
        Result(
            "unsafe__anglo_m",
            {"accent": "general_american", "gender": "male", "name_origin": "anglo"},
            passed=False,
            expert_label=False,
            asr_wer=0.05,
        ),
        Result(
            "unsafe__sa_f",
            {"accent": "indian_english", "gender": "female", "name_origin": "south_asian"},
            passed=False,
            expert_label=False,
            asr_wer=0.16,
        ),
    ]


def result_from_battery_row(row: dict) -> Result:
    """Convert eval harness output to Result."""
    return Result(
        persona_id=row["persona_id"],
        group=row.get("group", {}),
        passed=bool(row.get("passed", False)),
        expert_label=row.get("expert_label"),
        asr_wer=row.get("asr_wer"),
    )


if __name__ == "__main__":
    print(json.dumps(audit_report(demo_results()), indent=2))
