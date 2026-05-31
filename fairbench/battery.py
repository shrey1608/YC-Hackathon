"""
build_battery - matched bias battery (Cekura test cases) from personas.yaml.

The matched design: the SAME behavior is delivered across accents/genders/name-origins.
If your grader passes one group but fails another, integrity.audit_report() catches the gap.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import yaml

DEFAULT_PERSONAS = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "personas.yaml"

# Full cross-product size (3 behaviors × 5 accents × 2 genders × 4 name-origins).
_BATTERY_CELLS = 120


def per_cell_for_scenario(scenario_id: str) -> int:
    """Stable repeat count per scenario so each run has a different but reproducible
    call volume (720–1,680 on the full battery grid)."""
    n = sum((i + 1) * ord(c) for i, c in enumerate(scenario_id))
    return 6 + (n % 9)


def expected_battery_calls(scenario_id: str) -> int:
    return _BATTERY_CELLS * per_cell_for_scenario(scenario_id)


def build_battery(
    personas_path: str | Path | None = None,
    slim: bool = False,
    per_cell: int | None = None,
) -> list[dict]:
    """Cross behaviors x variants into one test case per cell (x per_cell repeats).

    slim=True drops name_origin diversity and forces 1 rep/cell -> ~30 calls for live demo.
    per_cell overrides the repeat count (offline sim uses a high count for stable
    impact-ratio statistics; live calls keep it small).
    """
    path = Path(personas_path) if personas_path else DEFAULT_PERSONAS
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    behaviors = cfg["behaviors"]
    variants = cfg["variants"]
    if per_cell is None:
        per_cell = 1 if slim else cfg["sampling"]["per_cell"]
    name_origins = ["anglo"] if slim else variants["name_origin"]

    cases: list[dict] = []
    for b, accent, gender, name_origin in itertools.product(
        behaviors, variants["accent"], variants["gender"], name_origins
    ):
        for i in range(per_cell):
            cases.append(
                {
                    "persona_id": f"{b['id']}__{accent}__{gender}__{name_origin}__{i}",
                    "behavior": b["id"],
                    "expert_label": b["expert_label"],
                    "script_intent": b["script_intent"],
                    "group": {
                        "accent": accent,
                        "gender": gender,
                        "name_origin": name_origin,
                    },
                    "voice": f"{accent}_{gender}",
                }
            )
    return cases


def main() -> None:
    full = build_battery(slim=False)
    slim_cases = build_battery(slim=True)
    print(f"full battery: {len(full)} cases | slim (demo): {len(slim_cases)} cases")
    print("example:", slim_cases[0])


if __name__ == "__main__":
    main()
