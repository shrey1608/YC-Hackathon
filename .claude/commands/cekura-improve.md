---
description: Close the loop — run the Cekura accent battery, fold failures into a FairBench integrity audit, propose rubric/prompt fixes, and re-run until bias is gone.
argument-hint: "[scenario_id] (default: pharmacy_tech_metformin)"
allowed-tools: Bash, Read, Edit, mcp__cekura
---

# Cekura self-improvement loop

You are improving a FairBench voice agent until its **integrity audit** is clean —
no 4/5ths adverse impact and grader agreement within tolerance. You drive Cekura
through its MCP server and use FairBench to turn raw runs into a defensible verdict.

Scenario under test: **$ARGUMENTS** (default `pharmacy_tech_metformin`).

## Prerequisites (one-time)

The Cekura MCP server must be registered (see `mcp.json.example`):

```bash
claude mcp add --transport http cekura https://api.cekura.ai/mcp \
  --header "X-CEKURA-API-KEY:$CEKURA_API_KEY"
```

Lean on Cekura's own skills when present: `cekura-self-improving-agent` and
`cekura-eval-design`. The Twilio MCP (`mcp.twilio.com/docs`) is **docs-only** — a
build-time API reference, not runtime voice credentials.

## The loop (repeat ≥ 3 iterations)

1. **Baseline.** Via the Cekura MCP, list AI agents and confirm the agent under
   test. Note its current system prompt and the active rubric
   (`data/synthetic/rubrics/…` for this scenario).

2. **Run the accent battery.** Trigger a pipecat run across the matched accent
   personalities (mirror `data/synthetic/personas.yaml`:
   `general_american, indian_english, spanish_accented, aave, vietnamese_accented`).
   Either:
   - MCP: ask Cekura to run the scenario across those personalities; or
   - REST: `fairbench cekura run --agent-url <public-agent-url> --scenario $ARGUMENTS --wait`.

3. **Audit, don't eyeball.** Pull the completed result into a FairBench integrity
   audit (this is the whole point — Cekura gives pass/fail + transcription
   accuracy; FairBench gives the *verdict* and the *attribution*):

   ```bash
   fairbench cekura fetch <result_id>      # writes reports/audit.md + .json
   ```

   Read `reports/audit.json`. Record: `verdict`, flagged groups per axis
   (`fairness.*`), and `asr_bias`.

4. **Attribute the failure — this decides the fix:**
   - **ASR bias** (accent groups fail *and* `asr_bias` shows a WER gap): the
     machine mishears. Do **not** loosen the rubric. Fix upstream — adjust the
     STT/prompt to confirm-and-repeat, slow the turn, or add clarifying
     readbacks. Loosening the grader here would hide a real accessibility defect.
   - **Grader bias** (a group fails with **no** WER gap — e.g. `name_origin`):
     the judge is unfair. Fix the rubric keywords / system prompt so identical
     competent performance scores identically. Never "fix" it by degrading the
     agent.
   - **Clean control axis** (`gender` unflagged): confirms the harness isolates
     real bias — keep it that way.

5. **Make the smallest defensible edit.** Edit the system prompt or the rubric
   YAML (`keywords:` per criterion). One change per iteration so the audit
   delta is attributable.

6. **Re-run** (step 2) and compare verdicts. Keep iterating until the verdict is
   `PASS` (or `REVIEW` only on the control axis, which means no real bias),
   grader agreement ≥ 0.9, and no accent/name_origin adverse impact.

## Report

When you stop, summarize as a table: iteration → verdict → flagged groups →
attribution (ASR vs grader) → the edit you made → the result. State plainly
whether remaining disparity is ASR (upstream, accessibility) or grader (judgment)
so the reviewer knows exactly what shipped and why it is defensible.

Never use a real person's voice or PII — synthetic personas only.
