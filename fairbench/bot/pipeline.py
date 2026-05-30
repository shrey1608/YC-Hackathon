"""
FairBench live voice pipeline (Pipecat).

Composition:  transport.input -> Nemotron ASR -> context -> Nemotron LLM ->
              Gradium TTS -> transport.output -> context

When the call ends the full transcript is graded against the active rubric and
saved as a synthetic session, so a live encounter flows into the same integrity
audit as the offline battery.

Requires `pip install -e ".[bot]"` plus pipecat-ai[gradium] and sponsor keys.
All pipecat imports are lazy so the rest of FairBench runs without it.
"""

from __future__ import annotations

from fairbench.adapters.pipeline import make_llm, make_stt, make_transport, make_tts
from fairbench.core.grader import SessionGrader
from fairbench.core.rubric import Rubric
from fairbench.core.scenario import Scenario
from fairbench.session import save_session


def build_task(scenario: Scenario, rubric: Rubric, transport=None):
    """Assemble the Pipecat PipelineTask and a grade-on-end handler.

    Returns (task, transport). Caller runs it with a PipelineRunner.
    """
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.processors.transcript_processor import TranscriptProcessor

    transport = transport or make_transport()
    stt = make_stt()
    llm = make_llm()
    tts = make_tts(scenario.persona.voice_hint)

    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": scenario.system_prompt},
            {"role": "assistant", "content": scenario.persona.opening_line},
        ]
    )
    context_aggregator = llm.create_context_aggregator(context)
    transcript = TranscriptProcessor()

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            transcript.user(),
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            transcript.assistant(),
            context_aggregator.assistant(),
        ]
    )
    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

    collected: list[dict] = []

    @transcript.event_handler("on_transcript_update")
    async def _on_update(_proc, frame):  # noqa: ANN001
        for msg in frame.messages:
            # the trainee is the human caller; the bot plays the patient
            role = "trainee" if msg.role == "user" else "patient"
            collected.append({"role": role, "text": msg.content})

    @transport.event_handler("on_client_disconnected")
    async def _on_end(_transport, _client):  # noqa: ANN001
        _grade_and_save(scenario, rubric, collected)
        await task.cancel()

    return task, transport


def _grade_and_save(scenario: Scenario, rubric: Rubric, turns: list[dict]) -> None:
    if not turns:
        return
    sid = save_session(
        scenario.id, turns, metadata={"source": "live", "transport": "voice"}
    )
    grade = SessionGrader(scenario, rubric).grade_transcript(sid, turns)
    print(f"\n[FairBench] session {sid} | overall {grade.overall} | pass {grade.passed}")
    print(f"[FairBench] scores: {grade.competency_scores}")


async def run_voice_bot(scenario: Scenario, rubric: Rubric) -> None:
    """Run the live pipeline to completion via the Pipecat runner."""
    from pipecat.pipeline.runner import PipelineRunner

    task, _transport = build_task(scenario, rubric)
    await PipelineRunner().run(task)
