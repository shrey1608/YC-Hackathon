"""
Twilio Media Streams bridge for the FairBench voice agent.

Two routes, both optional (the builder returns None — and the rest of the API
keeps working — if pipecat / the Twilio transport isn't installed):

  POST/GET  /api/twilio/voice  -> TwiML telling Twilio to open a Media Stream
                                  WebSocket back to this server.
  WS        /api/twilio/ws      -> the bidirectional audio stream. Runs the SAME
                                  Pipecat worker the browser call uses
                                  (Nemotron ASR -> Nemotron LLM -> Gradium TTS)
                                  and grades the transcript on hang-up.

Wiring (Twilio must reach this server over the public internet — e.g.
`ngrok http 8000`, or deploy to Pipecat Cloud):

  1. Point your Twilio number's Voice webhook (A CALL COMES IN) at
       https://<public-host>/api/twilio/voice         (HTTP POST)
  2. Put TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN in .env (the serializer uses them).
  3. Dial the number — Twilio opens the stream and the agent answers.

To pick a scenario per call, add a <Parameter name="scenario" value="..."/> to the
TwiML <Stream> (or set FAIRBENCH_SCENARIO on the server).
"""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request, Response, WebSocket
from loguru import logger


def build_twilio_router() -> APIRouter | None:
    """Return an APIRouter with the TwiML + media-stream routes, or None if the
    voice stack (pipecat) isn't installed."""
    try:
        from pipecat.frames.frames import LLMRunFrame  # noqa: F401
        from pipecat.workers.runner import WorkerRunner  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without [bot]
        logger.warning(f"Twilio bridge disabled (pipecat not installed): {exc}")
        return None

    router = APIRouter()

    @router.api_route("/api/twilio/voice", methods=["GET", "POST"])
    async def twilio_voice(request: Request) -> Response:
        """Return TwiML that bridges the call into our media-stream WebSocket."""
        host = request.headers.get("host") or request.url.netloc
        ws_url = f"wss://{host}/api/twilio/ws"
        scenario = os.environ.get("FAIRBENCH_SCENARIO", "")
        param = f'<Parameter name="scenario" value="{scenario}"/>' if scenario else ""
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Connect><Stream url="{ws_url}">{param}</Stream></Connect>'
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")

    @router.websocket("/api/twilio/ws")
    async def twilio_ws(websocket: WebSocket) -> None:
        await websocket.accept()

        # Twilio sends {"event":"connected"} then {"event":"start", "start":{...}}.
        # We must read the start frame first because the serializer needs the
        # streamSid to address audio back to the caller.
        start_info: dict | None = None
        while start_info is None:
            try:
                message = json.loads(await websocket.receive_text())
            except Exception:  # noqa: BLE001 - caller hung up before streaming
                await websocket.close()
                return
            event = message.get("event")
            if event == "start":
                start_info = message.get("start", {}) or {}
            elif event in ("stop", "closed"):
                await websocket.close()
                return

        stream_sid = start_info.get("streamSid")
        call_sid = start_info.get("callSid")
        custom = start_info.get("customParameters", {}) or {}
        if custom.get("scenario"):
            os.environ["FAIRBENCH_SCENARIO"] = str(custom["scenario"])

        from pipecat.frames.frames import TTSSpeakFrame
        from pipecat.workers.runner import WorkerRunner

        from fairbench.adapters.pipeline import make_transport
        from fairbench.bot.main import load_active_scenario
        from fairbench.bot.pipeline import build_worker

        scenario, rubric, _ = load_active_scenario()
        transport = make_transport(
            "twilio", websocket=websocket, stream_sid=stream_sid, call_sid=call_sid
        )
        worker, context = build_worker(scenario, rubric, transport)

        # Telephony has no RTVI client_ready, so kick off the greeting on connect.
        greeted = {"done": False}

        @transport.event_handler("on_client_connected")
        async def _greet(*_args):  # noqa: ANN002
            if greeted["done"]:
                return
            greeted["done"] = True
            context.add_message(
                {"role": "assistant", "content": scenario.persona.opening_line}
            )
            # Speak the opening line and wait for the caller (don't run the LLM
            # here — that makes the agent monologue past its greeting).
            await worker.queue_frames([TTSSpeakFrame(scenario.persona.opening_line)])

        logger.info(f"Twilio stream {stream_sid} (call {call_sid}) -> {scenario.id}")
        runner = WorkerRunner()
        await runner.add_workers(worker)
        await runner.run()

    logger.info("Twilio bridge /api/twilio/voice + /api/twilio/ws enabled")
    return router
