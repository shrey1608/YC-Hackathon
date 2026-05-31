"""
Custom SmallWebRTC signaling endpoint for the operable frontend.

Reuses pipecat's own SmallWebRTCRequestHandler (the exact code the dev runner
uses), so /api/offer builds + initializes the peer connection and hands it to our
bot() from fairbench.bot.pipeline. POST negotiates the offer/answer; PATCH carries
trickle-ICE candidates.

The HTTP bodies are our own Pydantic models (not pipecat's stdlib dataclasses) so
FastAPI treats them as request bodies, and we accept both camelCase (what the
JS client sends, e.g. ``requestData``) and snake_case. If pipecat is not
installed, build_webrtc_router() returns None and the rest of the API (audit,
sessions, scenarios, cekura) still works.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from fairbench.server.config import Settings


class OfferRequest(BaseModel):
    # Accept the JS client's camelCase (requestData/pcId/restartPc) and snake_case.
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    sdp: str
    type: str
    pc_id: str | None = Field(default=None, alias="pcId")
    restart_pc: bool | None = Field(default=None, alias="restartPc")
    request_data: Any | None = Field(default=None, alias="requestData")


def build_webrtc_router(settings: Settings):
    """Return an APIRouter exposing POST/PATCH /api/offer, or None if pipecat absent."""
    try:
        from aiortc import RTCIceServer
        from pipecat.runner.types import SmallWebRTCRunnerArguments
        from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
        from pipecat.transports.smallwebrtc.request_handler import (
            IceCandidate,
            SmallWebRTCPatchRequest,
            SmallWebRTCRequest,
            SmallWebRTCRequestHandler,
        )
    except ImportError as exc:  # pragma: no cover - exercised only without [bot]
        logger.warning(f"WebRTC disabled (pipecat not installed): {exc}")
        return None

    ice_servers = [RTCIceServer(urls=settings.stun_url)]
    if settings.turn_url:
        ice_servers.append(
            RTCIceServer(
                urls=settings.turn_url,
                username=settings.turn_username,
                credential=settings.turn_credential,
            )
        )
    handler = SmallWebRTCRequestHandler(ice_servers=ice_servers)

    router = APIRouter()

    @router.post("/api/offer")
    async def offer(req: OfferRequest, background_tasks: BackgroundTasks):
        session_id = str(uuid4())

        async def on_connection(connection: SmallWebRTCConnection):
            # Import lazily so the module loads even if bot deps are partial.
            from fairbench.bot.pipeline import bot

            background_tasks.add_task(
                bot,
                SmallWebRTCRunnerArguments(
                    webrtc_connection=connection,
                    body=req.request_data,
                    session_id=session_id,
                ),
            )

        return await handler.handle_web_request(
            request=SmallWebRTCRequest(
                sdp=req.sdp,
                type=req.type,
                pc_id=req.pc_id,
                restart_pc=req.restart_pc,
                request_data=req.request_data,
            ),
            webrtc_connection_callback=on_connection,
        )

    @router.patch("/api/offer")
    async def offer_patch(payload: dict):
        # Trickle ICE — accept camelCase or snake_case candidate fields.
        candidates = [
            IceCandidate(
                candidate=c.get("candidate", ""),
                sdp_mid=c.get("sdp_mid", c.get("sdpMid")),
                sdp_mline_index=c.get("sdp_mline_index", c.get("sdpMLineIndex")),
            )
            for c in payload.get("candidates", [])
        ]
        await handler.handle_patch_request(
            SmallWebRTCPatchRequest(
                pc_id=payload.get("pc_id", payload.get("pcId")),
                candidates=candidates,
            )
        )
        return {"status": "success"}

    logger.info("WebRTC /api/offer enabled")
    return router
