"""
NVIDIA Nemotron via an OpenAI-compatible endpoint (e.g. AWS).

Streaming + non-streaming chat completion. When no endpoint is configured the
adapter degrades to a deterministic mock so the text demo and grading pipeline
run fully offline.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class NemotronLLM:
    def __init__(self, endpoint: str, api_key: str | None = None, model: str = "nemotron"):
        self.endpoint = (endpoint or "").rstrip("/")
        self.api_key = api_key
        self.model = model

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _payload(self, messages: list[dict[str, str]], stream: bool, **kwargs: Any) -> dict:
        return {"model": self.model, "messages": messages, "stream": stream, **kwargs}

    async def stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        if not self.endpoint:
            yield self._mock_reply(messages)
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.endpoint}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=True, **kwargs),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or [{}]
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Non-streaming convenience: return the full assistant message."""
        if not self.endpoint:
            return self._mock_reply(messages)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.endpoint}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=False, **kwargs),
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _mock_reply(self, messages: list[dict[str, str]]) -> str:
        return (
            "I understand your concern, and I'm happy to help. Let me verify your "
            "prescription and confirm your identity, clarify the directions about "
            "taking it with food, and loop in the pharmacist to review this with you."
        )
