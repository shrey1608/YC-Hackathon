"""Load FairBench YAML config and resolve adapter drivers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    driver: str
    endpoint_env: str | None = None
    api_key_env: str | None = None
    model: str | None = None


class ServiceConfig(BaseModel):
    driver: str
    api_key_env: str | None = None
    voice: str | None = None


class TelephonyConfig(BaseModel):
    driver: str
    account_sid_env: str | None = None
    auth_token_env: str | None = None
    phone_number_env: str | None = None


class IntegrityConfig(BaseModel):
    four_fifths_threshold: float = 0.80
    reliability_min_kappa: float = 0.75
    asr_wer_delta_threshold: float = 0.10


class DataConfig(BaseModel):
    synthetic_only: bool = True
    rubrics_dir: str = "data/synthetic/rubrics"
    personas_dir: str = "data/synthetic/personas"
    labeled_turns: str = "data/synthetic/labeled_turns.json"


class FairBenchConfig(BaseModel):
    environment: str = "demo"
    llm: LLMConfig
    stt: ServiceConfig
    tts: ServiceConfig
    telephony: TelephonyConfig
    transport: dict[str, str] = Field(default_factory=lambda: {"default": "webrtc"})
    eval_battery: dict[str, Any] = Field(default_factory=dict)
    integrity: IntegrityConfig = Field(default_factory=IntegrityConfig)
    data: DataConfig = Field(default_factory=DataConfig)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> FairBenchConfig:
    config_path = path or os.environ.get("FAIRBENCH_CONFIG", "config/config.yaml")
    full = _project_root() / config_path if not Path(config_path).is_absolute() else Path(config_path)
    with full.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return FairBenchConfig.model_validate(raw)


def env(key: str | None) -> str | None:
    if not key:
        return None
    return os.environ.get(key)
