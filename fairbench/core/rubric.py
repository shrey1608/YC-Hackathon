"""Competency rubric definitions (synthetic / public standards only)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Criterion(BaseModel):
    id: str
    name: str
    description: str
    weight: float = 1.0
    pass_threshold: float = 0.7


class Rubric(BaseModel):
    id: str
    title: str
    criteria: list[Criterion] = Field(default_factory=list)

    def criterion_ids(self) -> list[str]:
        return [c.id for c in self.criteria]


def load_rubric(path: str | Path) -> Rubric:
    with Path(path).open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Rubric.model_validate(raw)
