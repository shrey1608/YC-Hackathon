"""Request/response schemas for the control-plane API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuditRunRequest(BaseModel):
    scenario: str = "pharmacy_tech_metformin"
    seed: int | None = None  # None -> the scenario's locked sim_seed
    per_cell: int = 8
    grader_name_bias_rate: float = 0.30


class AuditCompareRequest(BaseModel):
    """Before/after the self-improvement loop: same matched battery, graded by a
    biased grader (before) vs. a de-biased grader (after). The delta is the
    improvement — exactly what the audit catches then proves you fixed."""

    scenario: str = "pharmacy_tech_metformin"
    seed: int | None = None
    per_cell: int = 8
    before_bias_rate: float = 0.30  # grader under-credits some name origins
    after_bias_rate: float = 0.0  # mitigation applied


class Turn(BaseModel):
    role: str  # "trainee" | "patient"
    text: str


class GradeRequest(BaseModel):
    scenario_id: str
    turns: list[Turn]
    session_id: str | None = None


class CekuraRunRequest(BaseModel):
    scenario: str = "pharmacy_tech_metformin"
    # Cekura must reach the agent, so this is a public endpoint (Pipecat Cloud /
    # Twilio), never localhost. Absent -> the API explains the requirement.
    agent_url: str | None = None


class ScenarioInfo(BaseModel):
    id: str
    title: str
    domain: str
    pass_overall: float
    persona_name: str
    opening_line: str
    criteria: list[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    session_id: str
    scenario_id: str
    created_at: str | None = None
    source: str | None = None
    behavior: str | None = None
    accent: str | None = None
    passed: bool | None = None
    overall: float | None = None
    asr_wer: float | None = None
    turns: int = 0
