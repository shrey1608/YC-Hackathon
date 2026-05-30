"""
Pipecat service factories for FairBench.

Hackathon stack (yc-voice-agents-hackathon v2):
  STT  — Nemotron Speech Streaming (WebSocket, NVIDIA_ASR_URL)
  LLM  — Nemotron 3 Super (OpenAI-compatible, NEMOTRON_LLM_URL)
  TTS  — Gradium (GRADIUM_API_KEY)

Starter reference:
  https://github.com/pipecat-ai/yc-voice-agents-hackathon
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from fairbench.config import load_config

# Event-day defaults (unauthenticated) — override in .env if endpoints move
_DEFAULT_ASR_URL = "ws://44.241.251.184:8080"
_DEFAULT_LLM_URL = "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1"
_DEFAULT_LLM_MODEL = "nvidia/nemotron-3-super"


def make_llm():
    """Nemotron 3 Super via vLLM (OpenAI-compatible /v1)."""
    from fairbench.integrations.pipecat.nemotron_llm import VLLMOpenAILLMService

    enable_thinking = os.getenv("NEMOTRON_ENABLE_THINKING", "false").lower() == "true"
    model = os.getenv("NEMOTRON_LLM_MODEL", _DEFAULT_LLM_MODEL)
    return VLLMOpenAILLMService(
        api_key=os.getenv("NEMOTRON_LLM_API_KEY", "EMPTY"),
        base_url=os.environ.get("NEMOTRON_LLM_URL", _DEFAULT_LLM_URL),
        settings=VLLMOpenAILLMService.Settings(
            model=model,
            extra={
                "extra_body": {
                    "chat_template_kwargs": {"enable_thinking": enable_thinking},
                }
            },
        ),
    )


def make_stt():
    """Nemotron Speech Streaming ASR (WebSocket)."""
    from fairbench.integrations.pipecat.nvidia_stt import NVidiaWebSocketSTTService

    return NVidiaWebSocketSTTService(
        url=os.environ.get("NVIDIA_ASR_URL", _DEFAULT_ASR_URL),
        strip_interim_prefix=True,
    )


def make_tts(voice: str | None = None):
    """Gradium TTS."""
    from pipecat.services.gradium.tts import GradiumTTSService

    voice = voice or os.environ.get("GRADIUM_VOICE_ID") or load_config().tts.voice
    return GradiumTTSService(
        api_key=os.environ["GRADIUM_API_KEY"],
        settings=GradiumTTSService.Settings(
            voice=voice or "Eu9iL_CYe8N-Gkx_",
        ),
    )


def make_transport(transport: str | None = None, **kwargs):
    """SmallWebRTC for the local browser; Twilio websocket for telephony.

    pipecat >= 1.3 API: SmallWebRTC takes a webrtc_connection (supplied by the
    server's /api/offer handler or the dev runner) and a TransportParams.
    """
    transport = (transport or os.environ.get("FAIRBENCH_TRANSPORT", "webrtc")).lower()
    if transport == "twilio":
        from pipecat.serializers.twilio import TwilioFrameSerializer
        from pipecat.transports.websocket.fastapi import (
            FastAPIWebsocketParams,
            FastAPIWebsocketTransport,
        )

        websocket = kwargs.pop("websocket")
        return FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                serializer=TwilioFrameSerializer(
                    stream_sid=kwargs.get("stream_sid"),
                    call_sid=kwargs.get("call_sid"),
                    account_sid=os.environ.get("TWILIO_ACCOUNT_SID", ""),
                    auth_token=os.environ.get("TWILIO_AUTH_TOKEN", ""),
                ),
            ),
        )

    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

    return SmallWebRTCTransport(
        webrtc_connection=kwargs["webrtc_connection"],
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )


class EvalProvider(ABC):
    @abstractmethod
    def run_battery(self, agent_url: str, personas: list[dict]) -> list[dict]:
        """Run each persona; return rows with passed, expert_label, group, asr_wer."""
        ...


class CekuraEval(EvalProvider):
    """Pull a completed Cekura result or run the offline simulator."""

    def run_battery(self, agent_url: str, personas: list[dict]) -> list[dict]:
        result_id = os.environ.get("CEKURA_RESULT_ID")
        if os.environ.get("CEKURA_API_KEY") and result_id:
            from fairbench.adapters.eval.cekura import CekuraClient

            return CekuraClient().result_rows(result_id)
        from fairbench.sim.eval import SimulatedEval

        return SimulatedEval().run_battery(agent_url, personas)


def make_eval() -> EvalProvider:
    if os.environ.get("CEKURA_API_KEY"):
        return CekuraEval()
    from fairbench.sim.eval import SimulatedEval

    return SimulatedEval()
