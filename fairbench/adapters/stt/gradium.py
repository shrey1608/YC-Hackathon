"""
Gradium speech-to-text.

REST one-shot transcription per the Gradium API:
  POST https://api.gradium.ai/api/post/speech/asr
  header: x-api-key
  body:   raw audio bytes (Content-Type e.g. audio/wav)
  resp:   application/x-ndjson, lines carrying {"text"|"end_text": ...}

For the live Pipecat pipeline use pipecat.services.gradium.stt.GradiumSTTService;
this adapter is the standalone client FairBench uses to transcribe recorded turns
and measure word-error rate for the integrity audit.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx

ASR_URL = "https://api.gradium.ai/api/post/speech/asr"


class GradiumSTT:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GRADIUM_API_KEY")

    async def transcribe_file(
        self,
        audio: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> str:
        """One-shot transcription of complete audio. Returns the joined transcript."""
        if not self.api_key:
            raise RuntimeError("GRADIUM_API_KEY not set — cannot call Gradium STT")

        params = {}
        if language:
            params["json_config"] = json.dumps({"language": language})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                ASR_URL,
                headers={"x-api-key": self.api_key, "Content-Type": content_type},
                params=params,
                content=audio,
            )
            resp.raise_for_status()
            return self._join_ndjson(resp.text)

    @staticmethod
    def _join_ndjson(body: str) -> str:
        parts: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("error"):
                raise RuntimeError(f"Gradium STT error: {obj['error']}")
            chunk = obj.get("end_text") or obj.get("text")
            if chunk:
                parts.append(chunk)
        return " ".join(parts).strip()

    async def transcribe_stream(self, audio_frames: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Buffer frames and emit one transcript (REST). Live streaming uses Pipecat."""
        buf = bytearray()
        async for frame in audio_frames:
            buf.extend(frame)
        if buf and self.api_key:
            yield await self.transcribe_file(bytes(buf))


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein word-error rate of hypothesis vs reference (for ASR-bias audit)."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref:
        return 0.0 if not hyp else 1.0
    # classic DP edit distance over words
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cost = 0 if r == h else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return round(prev[-1] / len(ref), 3)
