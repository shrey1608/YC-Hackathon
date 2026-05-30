"""Service interfaces for LLM, STT, TTS, and eval."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        """Stream completion tokens from the model."""
        ...


@runtime_checkable
class STTProvider(Protocol):
    async def transcribe_stream(self, audio_frames: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Stream partial/final transcripts from audio."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    async def synthesize_stream(self, text: str, **kwargs: Any) -> AsyncIterator[bytes]:
        """Stream audio bytes for spoken text."""
        ...


@runtime_checkable
class EvalBattery(Protocol):
    async def run_persona_matrix(
        self,
        scenario_id: str,
        personas: list[dict[str, Any]],
        grader: Any,
    ) -> list[dict[str, Any]]:
        """Run matched personas (accent/voice/name/gender) and return raw results."""
        ...
