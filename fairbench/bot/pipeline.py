"""
FairBench live voice pipeline (Pipecat >= 1.3 worker API).

Composition:  transport.input -> Nemotron ASR -> user agg -> Nemotron LLM ->
              Gradium TTS -> transport.output -> assistant agg

The patient is voiced by Nemotron+Gradium; the human caller is the trainee. On
hang-up the standalone runner grades the transcript reconstructed from the
LLMContext and saves it as a synthetic session, so a live encounter flows into
the same integrity audit as the offline battery. (The browser path grades from
the client-captured transcript via POST /api/sessions/grade — see the server —
so grading never depends on pipecat transcript internals.)

All pipecat imports are lazy so the rest of FairBench runs without it.
"""

from __future__ import annotations

import os

from fairbench.adapters.pipeline import make_llm, make_stt, make_transport, make_tts
from fairbench.core.grader import SessionGrader
from fairbench.core.rubric import Rubric
from fairbench.core.scenario import Scenario
from fairbench.session import save_session

# Gradium TTS emits 48 kHz; Nemotron ASR wants 16 kHz (the vendored STT resamples in).
AUDIO_IN_SAMPLE_RATE = 16000
AUDIO_OUT_SAMPLE_RATE = 48000


def _text(content) -> str:  # noqa: ANN001
    """Flatten an OpenAI-style message content (str or list of parts) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in content]
        return " ".join(s for s in parts if s).strip()
    return "" if content is None else str(content)


def context_to_turns(messages: list[dict]) -> list[dict]:
    """Reconstruct FairBench turns from accumulated LLMContext messages.

    user -> trainee (the human caller being assessed); assistant -> patient
    (the synthetic counterpart). The system prompt is dropped.
    """
    turns: list[dict] = []
    for m in messages:
        role = m.get("role") if isinstance(m, dict) else None
        if role == "user":
            turns.append({"role": "trainee", "text": _text(m.get("content"))})
        elif role == "assistant":
            turns.append({"role": "patient", "text": _text(m.get("content"))})
    return [t for t in turns if t["text"]]


def build_worker(scenario: Scenario, rubric: Rubric, transport):
    """Assemble the PipelineWorker and wire greeting + grade-on-hangup."""
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import LLMRunFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        LLMContextAggregatorPair,
        LLMUserAggregatorParams,
    )

    stt = make_stt()
    llm = make_llm()
    tts = make_tts(scenario.persona.voice_hint)

    context = LLMContext([{"role": "system", "content": scenario.system_prompt}])
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            audio_in_sample_rate=AUDIO_IN_SAMPLE_RATE,
            audio_out_sample_rate=AUDIO_OUT_SAMPLE_RATE,
        ),
    )

    @worker.rtvi.event_handler("on_client_ready")
    async def _on_client_ready(*_args):  # noqa: ANN002
        # The patient opens the encounter, then we kick off the LLM turn.
        context.add_message({"role": "assistant", "content": scenario.persona.opening_line})
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _on_client_disconnected(*_args):  # noqa: ANN002
        _grade_and_save(scenario, rubric, context_to_turns(context.get_messages()))
        await worker.cancel()

    return worker, context


def _grade_and_save(scenario: Scenario, rubric: Rubric, turns: list[dict]) -> None:
    if not turns:
        return
    sid = save_session(scenario.id, turns, metadata={"source": "live", "transport": "voice"})
    grade = SessionGrader(scenario, rubric).grade_transcript(sid, turns)
    print(f"\n[FairBench] session {sid} | overall {grade.overall} | pass {grade.passed}")
    print(f"[FairBench] scores: {grade.competency_scores}")


async def bot(runner_args) -> None:  # noqa: ANN001
    """Pipecat runner entrypoint: build + run the worker for a connection.

    Branches on the runner argument type (browser WebRTC vs. telephony WebSocket)
    and reads the requested scenario from the request body.
    """
    from pipecat.runner.types import SmallWebRTCRunnerArguments, WebSocketRunnerArguments
    from pipecat.workers.runner import WorkerRunner

    # Lazy import avoids a bot.main <-> bot.pipeline import cycle.
    from fairbench.bot.main import load_active_scenario

    body = getattr(runner_args, "body", None) or {}
    if isinstance(body, dict) and body.get("scenario"):
        os.environ["FAIRBENCH_SCENARIO"] = str(body["scenario"])

    scenario, rubric, _cfg = load_active_scenario()

    if isinstance(runner_args, SmallWebRTCRunnerArguments):
        transport = make_transport("webrtc", webrtc_connection=runner_args.webrtc_connection)
    elif isinstance(runner_args, WebSocketRunnerArguments):
        transport = make_transport("twilio", websocket=runner_args.websocket)
    else:
        raise ValueError(f"Unsupported runner arguments: {type(runner_args).__name__}")

    worker, _context = build_worker(scenario, rubric, transport)
    runner = WorkerRunner()
    await runner.add_workers(worker)
    await runner.run()


if __name__ == "__main__":
    # `python -m fairbench.bot.pipeline` -> pipecat dev runner on :7860, bound to
    # bot() above (the runner finds `bot` on the __main__ module).
    from pipecat.runner.run import main

    main()
