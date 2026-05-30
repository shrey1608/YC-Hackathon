"""Pipecat services from pipecat-ai/yc-voice-agents-hackathon (BSD-2-Clause)."""

from fairbench.integrations.pipecat.nemotron_llm import VLLMOpenAILLMService
from fairbench.integrations.pipecat.nvidia_stt import NVidiaWebSocketSTTService

__all__ = ["VLLMOpenAILLMService", "NVidiaWebSocketSTTService"]
