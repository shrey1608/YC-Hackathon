"""
Gradium text-to-speech.

Uses the official ``gradium`` Python SDK when installed:
    client = gradium.client.GradiumClient(api_key=...)
    result = await client.tts(setup={"voice_id": ..., "output_format": "wav"}, text=...)
    result.raw_data  # audio bytes

For the live Pipecat pipeline use pipecat.services.gradium.tts.GradiumTTSService;
this adapter is the standalone client for generating synthetic-patient prompts.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

DEFAULT_VOICE = "YTpq7expH9539ERJ"


class GradiumTTS:
    def __init__(self, api_key: str | None = None, voice: str = DEFAULT_VOICE):
        self.api_key = api_key or os.environ.get("GRADIUM_API_KEY")
        self.voice = voice or DEFAULT_VOICE

    def _client(self):
        try:
            import gradium  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dep
            raise RuntimeError("gradium SDK not installed — run: pip install gradium") from exc
        if not self.api_key:
            raise RuntimeError("GRADIUM_API_KEY not set — cannot call Gradium TTS")
        return gradium.client.GradiumClient(api_key=self.api_key)

    async def synthesize(self, text: str, output_format: str = "wav", **kwargs: Any) -> bytes:
        """Return synthesized audio bytes for ``text``."""
        client = self._client()
        result = await client.tts(
            setup={"voice_id": self.voice, "output_format": output_format, **kwargs},
            text=text,
        )
        return result.raw_data

    async def synthesize_stream(self, text: str, **kwargs: Any) -> AsyncIterator[bytes]:
        """One-shot synthesis yielded as a single chunk. Live streaming uses Pipecat."""
        if not self.api_key:
            return
        yield await self.synthesize(text, **kwargs)
