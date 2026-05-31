# FairBench

**Does your voice AI grade everyone fairly?** FairBench gives an AI the *exact
same good answer* spoken in different accents, names, and genders — then checks
whether it passes everyone equally. When it doesn't, FairBench tells you **why**:
the speech‑to‑text mishearing an accent, or the AI judge under‑crediting a name.

Built on **Pipecat** (voice), **NVIDIA Nemotron** (open‑weights ASR + LLM),
**Gradium** (TTS), **Twilio** (phone), and **Cekura** (live‑call testing).
Runs end‑to‑end with **no API keys** on synthetic, public test personas.

## The problem

Voice AI now **scores people** — recruiter phone screens, clinical skill checks,
language tests. The scary part: the *same* correct answer can **pass** in one
voice and **fail** in another, and nobody notices.

A spoken evaluation can be unfair two very different ways, and FairBench
separates them:

| The two ways a spoken test can be unfair | What it looks like |
|---|---|
| 🎙️ **Transcription bias** — the speech‑to‑text mishears an accent, so a correct answer is garbled before it's ever scored | accent fails **with** a high mishear rate |
| ⚖️ **Grader bias** — the AI judge scores the same words lower because of a perceived identity (e.g. the name) | name fails **with no** mishear gap |

Gender is a **control group** that should stay flat — if it moves, the test is
noisy and we don't trust the result. That separation is the whole product.

## How it works

A person (or a test persona) gives a spoken answer; FairBench grades it on a
skills checklist, then proves the grade is **fair** using the EEOC **80% rule** (a
group passing less than 80% as often as the top group is a legal red flag).

The key move: because the **same competent answer** is delivered for every group,
any gap in who passes is the *AI's* flaw — not the person's. FairBench then
**attributes** each gap to the transcription (speech‑to‑text) or the judge (LLM),
so you fix the right thing. It **proves itself offline with no keys**, and the
*same* grading path runs live on real phone calls.

## Demo

**[▶ Watch the demo video](demo.mp4)** — ~60s walkthrough of the console (Cekura battery → bias audit → Improve before/after).

You hear the **same competent answer in two different voices** — then watch the
agent pass one and fail the other on identical words. That gap is the product:
FairBench measures it, attributes it to the transcriber or the judge, and (in the
**Improve** tab) closes the grader half in one click while the transcription gap
correctly stays flagged.

## Results: catching and closing grader bias

The **Improve** tab runs the matched battery before vs. after a grader fix in one
click. On the pharmacy scenario:

| Metric (pharmacy scenario) | Before fix | After fix |
|---|---|---|
| Name‑origin fairness ratio — Latino | **0.74** (flagged) | **0.92** (clear) |
| Name‑origin fairness ratio — South‑Asian | **0.78** (flagged) | **1.00** (clear) |
| Name‑origin groups flagged | **2** | **0** |
| Grader "wrongly failed" rate | 17.1% | 14.8% |
| Accent (transcription) groups flagged | 4 | **4 — unchanged, by design** |
| Gender control | clean | clean |

The accent gap **correctly persists** because a grader fix can't fix a
transcription problem — and gender stays clean throughout. Proving those two
behaviors at once is exactly what makes the result trustworthy.

## How it's built

- **Pipecat — voice.** The live call is a Pipecat pipeline:
  `transport → Nemotron ASR → Nemotron LLM → Gradium TTS → transport`. One
  `bot()` entrypoint serves **both** the browser (WebRTC) and a real phone
  (Twilio WebSocket). On hang‑up, the captured transcript is graded and saved —
  so a live call flows into the *same* audit as the offline test.
- **Nemotron — open weights.** Nemotron Speech Streaming is the ASR; Nemotron‑3‑
  Super is *both* the in‑call persona's voice **and** the LLM grader behind the
  checklist. Using an **open‑weights judge is the point** — a closed judge you
  can't inspect can't be audited for bias.
- **Cekura — live‑call testing.** Cekura drives a **matched battery** of real
  calls against the agent: identical competent scripts, varied only by accent and
  name. FairBench maps every call to a pass/fail row and renders the same fairness
  audit on real calls.

The fairness engine itself — fairness ratios, grader reliability, and the
transcription‑vs‑judge attribution — lives in
[`fairbench/core/integrity.py`](fairbench/core/integrity.py). The bias is
**never hard‑coded**: it emerges from the real grader running over
mis‑transcribed text, and the test suite asserts the engine catches it,
attributes it correctly, and raises no false alarm on the gender control.

## What we learned

- **The judge itself is a bias surface.** Most eval tooling treats the LLM grader
  as ground truth. Holding the spoken performance constant across groups made it
  obvious the *grader* can disagree with itself by name alone — which is why
  attribution (transcriber vs. judge) became the core of the project.
- **"Speak a line, then listen" is subtle in a voice pipeline.** The first build
  made the agent monologue past its own greeting; the fix was to speak a fixed
  `TTSSpeakFrame` and yield the turn instead of running the LLM immediately.
- **Transport parity is where the time goes.** Browser (WebRTC) and phone
  (Twilio) need different "first‑utterance" triggers; unifying them behind one
  worker took more care than the pipeline itself.
- **Keyless‑by‑default was worth it.** Making the whole audit prove itself offline
  (no API keys) means the demo, the tests, and the bias detection run anywhere —
  and the result is reproducible.

## Notes on the tools & models

Honest, firsthand notes from building on each.

**NVIDIA Nemotron (open weights).**
- *Did well:* the OpenAI‑compatible endpoint let **one adapter** serve both the
  conversational persona and the rubric grader — almost no glue code. Open weights
  are what made an *inspectable* judge possible, which is the entire premise of the
  audit: you can't audit a closed judge for bias.
- *Could be better:* strict structured/JSON output when grading was the main
  friction — we wanted a guaranteed JSON verdict and had to defend against drift.
  Clearer guidance on `NEMOTRON_ENABLE_THINKING` for grading consistency would
  help, and since the streaming ASR's accent robustness is *literally* what we
  measure, published accent benchmarks would let us calibrate.

**Cekura (self‑improvement loops).**
- *Worked well:* the matched accent/name battery maps cleanly onto fairness‑ratio
  rows, and pairing it with our transcription‑vs‑judge attribution made every fix
  targeted instead of guesswork — exactly the self‑improvement loop the platform
  is built for.
- *Could be better:* clearer **run status/result polling** semantics (knowing
  precisely when a battery is "done" and fetchable) and more consistent **metric
  naming** between the dashboard and the API, so mapping a run to pass/fail rows is
  unambiguous.

**Pipecat (voice orchestration).**
- *Worked well:* one `build_worker` served **both** browser
  (`SmallWebRTCTransport`) and a real phone (Twilio Media Streams) by swapping only
  the transport — phone + web from one pipeline. Hooking disconnect to
  grade‑on‑hangup was clean.
- *Friction — scripted greeting then listen:* seeding the opening line and queuing
  `LLMRunFrame` made the agent **monologue past its greeting**; we had to speak a
  `TTSSpeakFrame` and then wait. A documented recipe for "speak a fixed line, then
  yield the turn" would save hours.
- *Friction — transport parity:* WebRTC fires `on_client_ready`, but Twilio has no
  equivalent, so we kicked the greeting on `on_client_connected`. A consistent
  "first‑utterance" hook across transports would remove the guesswork.
- *Friction — transcript dedup:* `onBotOutput` fires per‑word **and** per‑sentence;
  we filtered on `aggregated_by === "sentence"` for a clean transcript.
- *Gotcha:* an embedded/Electron browser passes `getUserMedia` but sends **no
  audio** — the call connects and the agent hears silence. A transport‑level "no
  inbound audio" warning would have saved real debugging time.

---

# Get it running

## Quickest start — the keyless demo (≈60 seconds)

The product **proves itself offline with no API keys.** This runs a real audit
through the actual grader and writes the report to disk.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (use: source .venv/bin/activate on macOS/Linux)
pip install -e ".[dev]"

fairbench demo                    # writes reports/audit.{md,json} + sessions — no keys needed
pytest -q                         # runs the test suite, incl. the bias‑detection checks
```

`fairbench demo` runs:

```
same answer → spoken in many accents/names → accent mishearing → REAL grader → fairness audit
```

The bias **emerges** from the real grader running over mis‑transcribed text — it
is **not** hard‑coded. The tests assert the engine catches it, attributes it
correctly, and raises **no** false alarm on the untouched gender control.

## Full console (backend + dashboard)

The console is a tabbed web app backed by the FastAPI server.

```powershell
# Windows — one command starts the API (:8000) and the dashboard (:3000)
./scripts/dev.ps1
```

…or run the two processes yourself:

```powershell
pip install -e ".[bot,server,dev]"
fairbench-server                          # API on http://localhost:8000
cd dashboard; npm install; npm run dev    # dashboard on http://localhost:3000
```

Then open **http://localhost:3000**. The dashboard proxies
`/api/*` to the backend, so there's no CORS setup. Even with the backend down it
still shows the last saved audit, so you always see something real.

> New to the terminology? Every screen has tooltips, and the console header has a
> **"What do these terms mean?"** glossary that explains every term in plain English.

## Talk to it with your voice

- **In the browser** — open the **Live call** tab, allow your mic, and speak. (Use
  a real browser like Chrome/Edge at `http://localhost:3000`, not an in‑IDE
  preview, so the mic works.)
- **On a real phone (Twilio)** — add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
  and `TWILIO_PHONE_NUMBER` to `.env`. In the **Live call** tab, switch to phone
  mode, type your number, and hit **"Call me"** — FairBench dials your phone and
  the agent answers. For the *full interactive* agent (not just the opening line),
  expose the server with `ngrok http 8000` and set `PUBLIC_BASE_URL` to that https
  URL. On a Twilio trial account, verify your number first. The graded call shows
  up in **Sessions**.

---

# Use cases

Anywhere a voice AI decides who passes. Three that ship as scenarios:

### 💼 Recruiting phone screens
An AI screens candidates for a role. FairBench pushes the **same strong answer**
through the screen under many accents and names.
- **Catches:** candidates failing because the transcriber dropped a key word, or
  being under‑scored by the judge purely by name.
- **So what:** a phone screen is a legal hiring step. A group passing under 80% as
  often is bias you'd have to defend — caught **before** it's a liability.

### 💊 Pharmacy & clinical skill checks
A pharmacy tech handles a confused medication pickup. FairBench replays the same
safe response (verify identity → explain the interaction → loop in the pharmacist)
across accents and names.
- **Catches:** a mis‑heard word vs. a judge that under‑credits the identical script
  by name.
- **So what:** failing a competent tech over an accent is both a fairness **and** a
  patient‑safety problem. The score should reflect the answer, not the voice.

### 🩺 Nursing & licensure checks
A nurse escalates a deteriorating patient. FairBench replays the same urgent,
correct hand‑off across demographic variants.
- **Catches:** whether a missed step is the transcriber mishearing an accent or the
  grader discounting the nurse.
- **So what:** when the same competent escalation passes for some and fails for
  others, the **assessment** is broken — not the nurse.

**23 scenarios ship** in [`data/synthetic/scenarios/`](data/synthetic/scenarios/):
the pharmacy and nursing cases plus **20 hiring roles** across tech, sales,
healthcare, retail, finance, logistics, education, and hospitality. Pick any in
the **Audit**, **Live call**, or **Improve** tabs.

---

# Using the console (the 5 tabs)

| Tab | What it does |
|---|---|
| **Audit** | Pick a scenario, run the test, and read the verdict: who passed, the size of each gap, and **what's causing it** (transcription vs. judge), with a visible 0.80 fairness line. |
| **Live call** | Practice a real spoken conversation (browser or phone) with **live coaching** as you talk; hang up to get scored on the same checklist. |
| **Improve** | One click runs the test **before vs. after** a fix and proves the gap closed — while the transcription gap correctly persists and gender stays clean. |
| **Real calls** | Runs the matched battery as **real calls via Cekura** and renders the identical audit on live results. (Advanced: fetch an existing Cekura run by id.) |
| **Sessions** | Browse every graded conversation — score, scorecard, and transcript. |

---

# Reference

## Stack & environment

| Piece | Service | Env vars |
|---|---|---|
| Speech‑to‑text | [Nemotron Speech Streaming](https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b) | `NVIDIA_ASR_URL` |
| LLM (persona + grader) | [Nemotron 3 Super](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) | `NEMOTRON_LLM_URL`, `NEMOTRON_LLM_MODEL` |
| Text‑to‑speech | [Gradium](https://gradium.ai) | `GRADIUM_API_KEY` |
| Phone | Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` |
| Live‑call testing | Cekura | `CEKURA_API_KEY` |

Copy [`.env.example`](.env.example) to `.env`. The Nemotron URLs are prefilled
with the event‑day endpoints; the keyless demo and offline audit need **none** of
these.

## CLI

| Command | What it does |
|---|---|
| `fairbench demo` | Keyless self‑validating loop → audit + sessions |
| `fairbench audit` | Same audit (offline sim by default); `--demo`, `--results FILE`, `--live` |
| `fairbench battery` | Build the matched bias battery |
| `fairbench rubric` | Show the active skills checklist |
| `fairbench cekura fetch ID` | Pull a completed Cekura result → audit |
| `fairbench cekura run --agent-url URL` | Start a Cekura accent battery against a live agent |
| `fairbench-server` | Run the FastAPI backend (:8000) |

## Project layout

```
fairbench/
  core/        # checklist, grader, scenario, fairness engine
  sim/         # transcript generator + accent mishearing model + offline loop
  adapters/    # Nemotron LLM, Gradium TTS, Cekura client, Pipecat factories
  bot/         # text demo + live Pipecat pipeline
  server/      # FastAPI backend (audit, live call, improve, cekura, twilio)
data/synthetic/   # checklists, personas (bias battery), scenarios, demo sessions
dashboard/        # Next.js console
reports/          # generated audit.md / audit.json
```

> The Nemotron LLM/STT Pipecat service classes are vendored from NVIDIA's YC
> starter under `fairbench/integrations/pipecat/`; the Nemotron/Gradium endpoints
> are the starter's.

## Why it's different

Most eval tools tell you *whether* an agent passed. FairBench tells you *whether
the pass/fail is trustworthy*, and **separates the two ways it can be biased** —
the transcription vs. the judge — so a real disparity becomes a fixable,
defensible finding instead of a mystery.

## License

Proprietary.
