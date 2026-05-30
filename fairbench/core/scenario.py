"""Scenario engine — persona, system prompt, rubric binding."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from fairbench.core.rubric import Rubric, load_rubric


class Persona(BaseModel):
    name: str
    voice_hint: str | None = None
    accent: str | None = None
    gender: str | None = None
    opening_line: str


class Scenario(BaseModel):
    id: str
    title: str
    domain: str
    rubric_file: str
    system_prompt: str
    persona: Persona
    pass_overall: float = 0.75
    metadata: dict = Field(default_factory=dict)

    def rubric_path(self, rubrics_dir: str | Path) -> Path:
        return Path(rubrics_dir) / self.rubric_file

    def load_rubric(self, rubrics_dir: str | Path) -> Rubric:
        return load_rubric(self.rubric_path(rubrics_dir))


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Scenario.model_validate(raw)
