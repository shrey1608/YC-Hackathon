"""Load active rubric block from data/synthetic/rubrics.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_RUBRICS = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "rubrics.yaml"


def load_rubrics_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_RUBRICS
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def active_rubric(path: str | Path | None = None) -> tuple[str, dict]:
    cfg = load_rubrics_config(path)
    key = cfg["active"]
    return key, cfg[key]
