# FairBench

**Voice competency training with integrity auditing.** Trainees run live spoken
encounters against competency rubrics; FairBench then proves the scoring is fair —
impact ratios (EEOC 4/5ths rule), grader reliability vs. expert labels, and ASR-bias
flags — so every pass/fail is defensible. Synthetic personas and public rubrics only.

Built on Pipecat, NVIDIA Nemotron (AWS), Gradium, Twilio, and Cekura.

---

## Why it's different

Most eval tools tell you *whether* an agent passed. FairBench tells you *whether
the pass/fail is trustworthy*, and **separates the two ways it can be biased**:

- **ASR bias** — accented speech is transcribed worse, so identical competent
  performance silently fails. Shows up as accent adverse impact **with a matching
  word-error-rate gap**.
- **Grader bias** — the LLM judge under-credits certain names. Shows up as
  name-origin adverse impact **with no WER gap** — so you know it's the grader, not
  the microphone.

The integrity engine ([fairbench/core/integrity.py](fairbench/core/integrity.py))
quantifies both and renders an audit you can hand to compliance.

## Self-validating — runs with zero keys

The product validates itself offline. `fairbench demo` runs the matched bias
battery through a real pipeline:

```
matched persona → synthetic transcript → accent ASR degradation → REAL grader → integrity audit
```

Bias **emerges** from the actual grader running over accent-degraded text — it is
not hard-coded. The test suite asserts the engine catches it and attributes it
correctly (and raises no false alarms on the untouched gender control).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -e ".[dev]"

fairbench demo                    # writes reports/audit.{md,json} + sessions, no keys needed
pytest -q                         # 15 tests, incl. the emergent-bias validation matrix
```

Example verdict (seed-locked fixture):

| Axis | Result | Mechanism |
|------|--------|-----------|
| accent | general_american 78% vs spanish 22% — **flagged** | ASR (matching WER gap) |
| name_origin | latino/south_asian **flagged** (IR 0.74 / 0.78) | grader (no WER gap) |
| gender | female 48.7% = male 48.7% — clean | untouched control |
| reliability | grader false-fails 17% of competent performances | — |

## Dashboard

```bash
cd dashboard
npm install
npm run dev          # http://localhost:3000  (reads ../reports/audit.json + ../.sessions)
```

Verdict banner, per-group impact-ratio bars, reliability, ASR-bias, and the same
competent performance graded across accents.

## Hackathon stack (YC voice agents)

FairBench uses the same **Version 2** stack as the official starter:

| Piece | Service | Env vars |
|-------|---------|----------|
| STT | [Nemotron Speech Streaming](https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b) | `NVIDIA_ASR_URL` |
| LLM | [Nemotron 3 Super](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) | `NEMOTRON_LLM_URL`, `NEMOTRON_LLM_MODEL` |
| TTS | [Gradium](https://gradium.ai) | `GRADIUM_API_KEY` |

Event-day endpoints are **unauthenticated** — defaults are in `.env.example` from the
[starter README (Version 2)](https://github.com/pipecat-ai/yc-voice-agents-hackathon/blob/main/README.md#version-2).
Pipecat service classes are vendored under `fairbench/integrations/pipecat/` from
[`nemotron_llm.py`](https://github.com/pipecat-ai/yc-voice-agents-hackathon/blob/main/server/nemotron_llm.py) and
[`nvidia_stt.py`](https://github.com/pipecat-ai/yc-voice-agents-hackathon/blob/main/server/nvidia_stt.py).

### MCP in Cursor (optional — for building, not runtime)

| MCP | URL | Auth | Purpose |
|-----|-----|------|---------|
| [Cekura](https://docs.cekura.ai/mcp/overview) | `https://api.cekura.ai/mcp` | `CEKURA_API_KEY` or OAuth | Run `/cekura-report`, wire Pipecat agent tests |
| [Twilio docs](https://www.twilio.com/docs/ai/mcp) | `https://mcp.twilio.com/docs` | None | API search only — **not** your voice credentials |

Copy [mcp.json.example](mcp.json.example) into Cursor MCP settings. Cekura skills:
[github.com/cekura-ai/cekura-skills](https://github.com/cekura-ai/cekura-skills).

### Live voice encounter

```bash
pip install -e ".[bot]"
copy .env.example .env            # Gradium + Cekura keys; Nemotron URLs prefilled

# Offline text demo (no voice keys required)
set FAIRBENCH_TRANSPORT=text
fairbench-bot

# Live WebRTC in browser (clone starter for full runner UI, or use fairbench-bot)
set FAIRBENCH_TRANSPORT=webrtc
fairbench-bot
```

Pipeline: `transport → Nemotron ASR → Nemotron LLM → Gradium TTS → transport`. On
hang-up the transcript is graded and saved ([fairbench/bot/pipeline.py](fairbench/bot/pipeline.py)).

**Phone demo:** needs `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and Pipecat Cloud deploy —
follow the [starter Twilio + Pipecat Cloud section](https://github.com/pipecat-ai/yc-voice-agents-hackathon#deploy-to-pipecat-cloud).
There is no separate “Pipecat API key”; use `pc cloud auth login` from the [Pipecat CLI](https://github.com/pipecat-ai/pipecat-cli).

## Auditing a real Cekura run

Cekura sweeps accent *personalities* and scores a **Transcription Accuracy** metric
per run — exactly FairBench's per-accent signal.

```bash
set CEKURA_API_KEY=...
set CEKURA_RESULT_ID=12345         # a completed Cekura accent-test result
fairbench audit --live             # pulls the result, maps it, audits it
```

## CLI

| Command | What it does |
|---------|--------------|
| `fairbench demo` | Offline self-validating loop → audit + sessions |
| `fairbench audit` | Same audit (default sim); `--demo`, `--results FILE`, `--live` |
| `fairbench battery --slim` | Build the matched bias battery (~30 cases for live calls) |
| `fairbench rubric` | Show the active rubric |

## Switch scenario (pharmacy → nursing SBAR)

Set `active:` in [data/synthetic/rubrics.yaml](data/synthetic/rubrics.yaml), or
`FAIRBENCH_SCENARIO=nursing_sbar_handoff` for the bot. The grader and simulator
detect the SBAR domain automatically.

## Layout

```
fairbench/
  core/        # rubric, grader, scenario, integrity engine
  sim/         # transcript generator + accent ASR model + SimulatedEval (offline loop)
  adapters/    # Nemotron LLM, Gradium STT/TTS, Cekura client, Pipecat factories
  bot/         # text demo + live Pipecat pipeline
config/config.yaml
data/synthetic/   # rubrics, personas (bias battery), scenarios, demo sessions
dashboard/        # Next.js audit viewer
reports/          # generated audit.md / audit.json
```

## Components

| Component | Provider |
|-----------|----------|
| Orchestration | Pipecat + Pipecat Cloud |
| LLM | NVIDIA Nemotron (AWS, OpenAI-compatible) |
| STT | Nemotron Speech Streaming (WebSocket) |
| TTS | Gradium (`pipecat-ai[gradium]`) |
| Telephony | Twilio |
| Eval battery | Cekura |
| Integrity math | FairBench ([fairbench/core/integrity.py](fairbench/core/integrity.py)) |

## Judge pitch

> FairBench scores live voice encounters against competency rubrics, then proves the
> scoring is fair — impact ratios, grader reliability, and ASR-bias flags that tell
> you whether a disparity is your transcription or your judge. It validates itself
> offline with synthetic data, and the same path runs live on Pipecat, Nemotron,
> Gradium, Twilio, and Cekura.

## License

Proprietary.
