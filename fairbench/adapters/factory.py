"""Instantiate adapters from FairBench config."""

from __future__ import annotations

from fairbench.config import FairBenchConfig, env, load_config
from fairbench.core.protocols import LLMProvider, STTProvider, TTSProvider


def create_llm(config: FairBenchConfig | None = None) -> LLMProvider:
    cfg = config or load_config()
    driver = cfg.llm.driver

    if driver == "nvidia_nemotron":
        from fairbench.adapters.llm.nemotron import NemotronLLM

        import os

        endpoint = env(cfg.llm.endpoint_env) or os.getenv("NEMOTRON_LLM_URL", "")
        return NemotronLLM(
            endpoint=endpoint,
            api_key=env(cfg.llm.api_key_env) or os.getenv("NEMOTRON_LLM_API_KEY"),
            model=os.getenv("NEMOTRON_LLM_MODEL", cfg.llm.model or "nvidia/nemotron-3-super"),
        )

    raise ValueError(f"Unknown LLM driver: {driver}")


def create_stt(config: FairBenchConfig | None = None) -> STTProvider:
    cfg = config or load_config()
    driver = cfg.stt.driver

    if driver == "gradium":
        from fairbench.adapters.stt.gradium import GradiumSTT

        return GradiumSTT(api_key=env(cfg.stt.api_key_env))

    raise ValueError(f"Unknown STT driver: {driver}")


def create_tts(config: FairBenchConfig | None = None) -> TTSProvider:
    cfg = config or load_config()
    driver = cfg.tts.driver

    if driver == "gradium":
        from fairbench.adapters.tts.gradium import GradiumTTS

        return GradiumTTS(
            api_key=env(cfg.tts.api_key_env),
            voice=cfg.tts.voice or "default",
        )

    raise ValueError(f"Unknown TTS driver: {driver}")
