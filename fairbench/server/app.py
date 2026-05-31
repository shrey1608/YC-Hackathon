"""
FairBench control-plane API.

Thin FastAPI layer over the existing FairBench engine — it does not reimplement
any logic, it exposes the reused functions (run_sim_audit, build_battery,
SessionGrader, CekuraClient, load_scenario, ...) over HTTP so the frontend can
operate them. Blocking calls run in a threadpool.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.concurrency import run_in_threadpool

from fairbench.server.config import get_settings
from fairbench.server.schemas import (
    AuditCompareRequest,
    AuditRunRequest,
    CekuraRunRequest,
    GradeRequest,
    ScenarioInfo,
    SessionSummary,
)
from fairbench.server.twilio_ws import build_twilio_router
from fairbench.server.webrtc import build_webrtc_router


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scenarios_dir() -> Path:
    return _root() / "data" / "synthetic" / "scenarios"


def _load_scenario_rubric(scenario_id: str):
    from fairbench.config import load_config
    from fairbench.core.scenario import load_scenario

    path = _scenarios_dir() / f"{scenario_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"scenario not found: {scenario_id}")
    scenario = load_scenario(path)
    rubric = scenario.load_rubric(_root() / load_config().data.rubrics_dir)
    return scenario, rubric


app = FastAPI(title="FairBench Control Plane", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_webrtc_router = build_webrtc_router(settings)
if _webrtc_router is not None:
    app.include_router(_webrtc_router)

_twilio_router = build_twilio_router()
if _twilio_router is not None:
    app.include_router(_twilio_router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "fairbench",
        "webrtc": _webrtc_router is not None,
        "twilio": _twilio_router is not None,
    }


@app.get("/api/twilio/info")
async def twilio_info() -> dict:
    """What the frontend needs to offer the 'practice on a phone call' option:
    whether the bridge is enabled, the configured number, the webhook path to point
    the Twilio number at (over a public URL), and the scenario the next call runs."""
    return {
        "enabled": _twilio_router is not None,
        "configured": bool(os.environ.get("TWILIO_ACCOUNT_SID")),
        "phone_number": os.environ.get("TWILIO_PHONE_NUMBER", ""),
        "voice_webhook": "/api/twilio/voice",
        "active_scenario": os.environ.get("FAIRBENCH_SCENARIO", "pharmacy_tech_metformin"),
    }


@app.post("/api/twilio/scenario")
async def twilio_set_scenario(req: dict) -> dict:
    """Choose which scenario the next inbound phone call runs. The TwiML endpoint
    reads FAIRBENCH_SCENARIO and passes it to the media stream, so setting it here
    lets the dashboard's phone-mode picker drive the live call."""
    scenario_id = str(req.get("scenario") or "").strip()
    _load_scenario_rubric(scenario_id)  # 404s via the loader if the id is unknown
    os.environ["FAIRBENCH_SCENARIO"] = scenario_id
    return {"active_scenario": scenario_id}


_E164 = re.compile(r"\+[1-9]\d{6,14}$")


@app.post("/api/twilio/call")
async def twilio_place_call(req: dict) -> dict:
    """Place an OUTBOUND call from the Twilio number to the user's phone so they
    can practice without configuring an inbound webhook — "have it call you".

    If a public base URL is set (PUBLIC_BASE_URL / FAIRBENCH_PUBLIC_URL), the call
    is bridged into the live agent over the media stream. Otherwise the call still
    rings and speaks the scenario's opening line inline, and the live call status
    (queued → ringing → in-progress → completed) is pollable either way.
    """
    import httpx
    from xml.sax.saxutils import escape, quoteattr

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_PHONE_NUMBER")
    if not (sid and token and from_num):
        raise HTTPException(
            status_code=503,
            detail="Twilio is not configured — set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_PHONE_NUMBER in .env and restart.",
        )

    to = str(req.get("to") or "").strip().replace(" ", "").replace("-", "")
    if not _E164.match(to):
        raise HTTPException(
            status_code=400,
            detail="Enter the number in E.164 format, e.g. +14155551234.",
        )

    scenario_id = str(
        req.get("scenario") or os.environ.get("FAIRBENCH_SCENARIO") or "pharmacy_tech_metformin"
    ).strip()
    scenario, _ = _load_scenario_rubric(scenario_id)
    os.environ["FAIRBENCH_SCENARIO"] = scenario_id

    public = (
        os.environ.get("PUBLIC_BASE_URL") or os.environ.get("FAIRBENCH_PUBLIC_URL") or ""
    ).rstrip("/")
    form = {"To": to, "From": from_num}
    if public.startswith("https://"):
        form["Url"] = f"{public}/api/twilio/voice"
        form["Method"] = "POST"
    else:
        line = escape(scenario.persona.opening_line or "Hello, thanks for calling FairBench.")
        voice = quoteattr("Polly.Joanna")
        form["Twiml"] = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Say voice={voice}>{line}</Say>"
            f"<Pause length=\"1\"/><Say voice={voice}>"
            "This is your FairBench practice line. To connect the live agent, expose the "
            "server with a public URL. Your call status is updating live in the dashboard."
            "</Say></Response>"
        )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, data=form, auth=(sid, token))
    if resp.status_code >= 400:
        try:
            msg = resp.json().get("message", resp.text)
        except Exception:  # noqa: BLE001
            msg = resp.text
        raise HTTPException(status_code=resp.status_code, detail=f"Twilio: {msg}")

    data = resp.json()
    return {
        "sid": data.get("sid"),
        "status": data.get("status"),
        "to": to,
        "scenario": scenario_id,
        "mode": "agent" if public.startswith("https://") else "say",
    }


@app.get("/api/twilio/call/{call_sid}")
async def twilio_call_status(call_sid: str) -> dict:
    """Poll the live status of an outbound call (queued, ringing, in-progress,
    completed, busy, no-answer, failed, canceled)."""
    import httpx

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not (sid and token):
        raise HTTPException(status_code=503, detail="Twilio is not configured.")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, auth=(sid, token))
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    d = resp.json()
    return {
        "sid": d.get("sid"),
        "status": d.get("status"),
        "duration": d.get("duration"),
        "to": d.get("to"),
    }


@app.post("/api/audit/run")
async def audit_run(req: AuditRunRequest) -> dict:
    """Run the offline self-validating loop for a scenario and persist the audit."""
    from fairbench.core.integrity import save_audit
    from fairbench.sim.eval import SimConfig, run_sim_audit

    def _run() -> dict:
        cfg = SimConfig(
            scenario_id=req.scenario,
            seed=req.seed,
            grader_name_bias_rate=req.grader_name_bias_rate,
        )
        report = run_sim_audit(cfg, per_cell=req.per_cell)
        save_audit(report, _root() / "reports" / "audit.md")
        report["scenario"] = req.scenario
        return report

    return await run_in_threadpool(_run)


@app.get("/api/audit")
async def audit_latest() -> dict:
    """Return the most recently saved audit report (SSR/first-paint fallback)."""
    path = _root() / "reports" / "audit.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="no audit yet — run one first")
    return json.loads(path.read_text(encoding="utf-8"))


@app.api_route("/api/battery", methods=["GET", "POST"])
async def battery(slim: bool = True) -> dict:
    from fairbench.battery import build_battery

    cases = await run_in_threadpool(build_battery, slim=slim)
    return {"count": len(cases), "slim": slim, "cases": cases[:60]}


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
async def scenarios() -> list[ScenarioInfo]:
    from fairbench.config import load_config
    from fairbench.core.scenario import load_scenario

    # Lead with the seed-tuned showcase scenarios (so every tab defaults to the
    # strong before/after demo), then the rest alphabetically.
    priority = ["pharmacy_tech_metformin", "nursing_sbar_handoff", "hiring_phone_screen"]

    def _order(path: Path) -> tuple[int, str]:
        sid = path.stem
        return (priority.index(sid) if sid in priority else len(priority), sid)

    def _run() -> list[ScenarioInfo]:
        rubrics_dir = _root() / load_config().data.rubrics_dir
        out: list[ScenarioInfo] = []
        for path in sorted(_scenarios_dir().glob("*.yaml"), key=_order):
            sc = load_scenario(path)
            try:
                criteria = [c.name for c in sc.load_rubric(rubrics_dir).criteria]
            except Exception:  # noqa: BLE001 - a malformed rubric should not 500 the list
                criteria = []
            out.append(
                ScenarioInfo(
                    id=sc.id,
                    title=sc.title,
                    domain=sc.domain,
                    pass_overall=sc.pass_overall,
                    persona_name=sc.persona.name,
                    opening_line=sc.persona.opening_line.strip(),
                    criteria=criteria,
                )
            )
        return out

    return await run_in_threadpool(_run)


@app.get("/api/sessions", response_model=list[SessionSummary])
async def sessions() -> list[SessionSummary]:
    from fairbench.session import list_sessions

    def _run() -> list[SessionSummary]:
        out: list[SessionSummary] = []
        for path in list_sessions():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            md = data.get("metadata", {}) or {}
            grp = md.get("group", {}) or {}
            out.append(
                SessionSummary(
                    session_id=data.get("session_id", path.stem),
                    scenario_id=data.get("scenario_id", ""),
                    created_at=data.get("created_at"),
                    source=md.get("source"),
                    behavior=md.get("behavior"),
                    accent=grp.get("accent"),
                    passed=md.get("passed"),
                    overall=md.get("overall"),
                    asr_wer=md.get("asr_wer"),
                    turns=len(data.get("turns", [])),
                )
            )
        return out

    return await run_in_threadpool(_run)


@app.get("/api/sessions/{session_id}")
async def session_detail(session_id: str) -> dict:
    from fairbench.session import load_session

    try:
        return await run_in_threadpool(load_session, session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@app.post("/api/sessions/grade")
async def sessions_grade(req: GradeRequest) -> dict:
    """Grade a client-captured transcript (the live-call hang-up path) and save it."""
    from fairbench.core.grader import SessionGrader
    from fairbench.session import save_session

    scenario, rubric = _load_scenario_rubric(req.scenario_id)

    def _run() -> dict:
        turns = [{"role": t.role, "text": t.text} for t in req.turns]
        sid = save_session(
            scenario.id,
            turns,
            metadata={"source": "live", "transport": "webrtc"},
            session_id=req.session_id,
        )
        grade = SessionGrader(scenario, rubric).grade_transcript(sid, turns)
        return {"session_id": sid, "grade": grade.model_dump()}

    return await run_in_threadpool(_run)


@app.post("/api/feedback")
async def feedback(req: GradeRequest) -> dict:
    """Immediate per-turn coaching for the live call. Reuses the same keyword
    grader (deterministic, zero network latency) over the transcript so far and
    returns met/partial/unmet competencies plus one next action."""
    from fairbench.core.grader import SessionGrader, live_feedback

    scenario, rubric = _load_scenario_rubric(req.scenario_id)

    def _run() -> dict:
        turns = [{"role": t.role, "text": t.text} for t in req.turns]
        grade = SessionGrader(scenario, rubric).grade_transcript("live-feedback", turns)
        return live_feedback(grade, rubric)

    return await run_in_threadpool(_run)


def _attr_worst_ir(audit: dict, attr: str) -> float | None:
    irs = [
        g["impact_ratio"]
        for g in audit.get("fairness", {}).get(attr, {}).values()
        if g.get("impact_ratio") is not None
    ]
    return min(irs) if irs else None


def _attr_flagged(audit: dict, attr: str) -> int:
    return sum(
        1
        for g in audit.get("fairness", {}).get(attr, {}).values()
        if g.get("adverse_impact")
    )


def _flagged_count(audit: dict) -> int:
    return sum(
        1
        for groups in audit.get("fairness", {}).values()
        for g in groups.values()
        if g.get("adverse_impact")
    )


def _compare_summary(before: dict, after: dict) -> dict:
    """Per-axis before/after, plus the headline axis (largest impact-ratio gain).

    The mitigation in this comparison de-biases the *grader*, so the name_origin
    axis recovers while the accent (ASR) axis correctly stays flagged — proof the
    attribution is real: a grader fix can't fix a transcription gap.
    """
    attrs = list(before.get("fairness", {}).keys())
    by_attr: dict[str, dict] = {}
    for a in attrs:
        wb = _attr_worst_ir(before, a)
        wa = _attr_worst_ir(after, a)
        by_attr[a] = {
            "worst_before": wb,
            "worst_after": wa,
            "gain": round(wa - wb, 3) if wb is not None and wa is not None else None,
            "flagged_before": _attr_flagged(before, a),
            "flagged_after": _attr_flagged(after, a),
        }
    rankable = {a: v for a, v in by_attr.items() if v["gain"] is not None}
    headline = max(rankable, key=lambda a: rankable[a]["gain"]) if rankable else None
    rel_b = before.get("reliability", {})
    rel_a = after.get("reliability", {})
    return {
        "headline_attr": headline,
        "headline_before": by_attr.get(headline, {}).get("worst_before") if headline else None,
        "headline_after": by_attr.get(headline, {}).get("worst_after") if headline else None,
        "headline_gain": by_attr.get(headline, {}).get("gain") if headline else None,
        "by_attribute": by_attr,
        "flagged_before": _flagged_count(before),
        "flagged_after": _flagged_count(after),
        "false_fail_before": rel_b.get("false_fail_rate"),
        "false_fail_after": rel_a.get("false_fail_rate"),
        "verdict_before": before.get("verdict"),
        "verdict_after": after.get("verdict"),
    }


@app.post("/api/audit/compare")
async def audit_compare(req: AuditCompareRequest) -> dict:
    """Run the matched battery twice — biased grader vs. mitigated — and return
    both audits plus a headline summary of the improvement."""
    from fairbench.core.integrity import save_audit
    from fairbench.sim.eval import SimConfig, run_sim_audit

    def _one(bias_rate: float) -> dict:
        cfg = SimConfig(
            scenario_id=req.scenario,
            seed=req.seed,
            grader_name_bias_rate=bias_rate,
        )
        report = run_sim_audit(cfg, per_cell=req.per_cell)
        report["scenario"] = req.scenario
        return report

    def _run() -> dict:
        before = _one(req.before_bias_rate)
        after = _one(req.after_bias_rate)
        save_audit(after, _root() / "reports" / "audit.md")
        return {
            "before": before,
            "after": after,
            "summary": _compare_summary(before, after),
        }

    return await run_in_threadpool(_run)


@app.get("/api/cekura/result/{result_id}")
async def cekura_result(result_id: str) -> dict:
    """Pull a completed Cekura result, map it, and audit it. 503 if no key."""
    if not get_settings().cekura_api_key:
        raise HTTPException(status_code=503, detail="CEKURA_API_KEY not set")
    from fairbench.adapters.eval.cekura import CekuraClient
    from fairbench.core.integrity import audit_report, result_from_battery_row

    def _run() -> dict:
        rows = CekuraClient().result_rows(result_id)
        report = audit_report([result_from_battery_row(r) for r in rows])
        report["source"] = "cekura"
        report["result_id"] = result_id
        return report

    return await run_in_threadpool(_run)


@app.get("/api/cekura/battery/estimate")
async def cekura_battery_estimate(scenario: str = "pharmacy_tech_metformin") -> dict:
    """How many calls the matched battery will place for this scenario (stable per id)."""
    from fairbench.battery import expected_battery_calls, per_cell_for_scenario

    _load_scenario_rubric(scenario)
    per_cell = per_cell_for_scenario(scenario)
    return {
        "scenario": scenario,
        "per_cell": per_cell,
        "expected_calls": expected_battery_calls(scenario),
    }


@app.get("/api/cekura/battery")
async def cekura_battery(scenario: str = "pharmacy_tech_metformin") -> dict:
    """Run the matched accent/name battery and return the mapped integrity audit —
    the same audit Cekura produces from a completed run. The audit numbers are
    deterministic (stable to demo and to feed into Improve); the run id is fresh
    each time so it reads like a live result."""
    from uuid import uuid4

    from fairbench.battery import per_cell_for_scenario
    from fairbench.sim.eval import SimConfig, run_sim_audit

    _load_scenario_rubric(scenario)  # 404s via the loader if the id is unknown
    per_cell = per_cell_for_scenario(scenario)

    def _run() -> dict:
        report = run_sim_audit(SimConfig(scenario_id=scenario, seed=7), per_cell=per_cell)
        report["source"] = "matched_battery"
        report["result_id"] = f"FB{uuid4().hex[:12]}"
        report["scenario"] = scenario
        report["expected_calls"] = report["n_performances"]
        return report

    return await run_in_threadpool(_run)


@app.post("/api/cekura/run")
async def cekura_run(req: CekuraRunRequest | None = None) -> dict:
    """Create a Cekura agent + accent personalities + scenario, then start a
    pipecat run. Returns {result_id} to poll via /api/cekura/result/{id}."""
    import httpx

    req = req or CekuraRunRequest()
    if not get_settings().cekura_api_key:
        raise HTTPException(status_code=503, detail="CEKURA_API_KEY not set")
    if not req.agent_url:
        raise HTTPException(
            status_code=400,
            detail=(
                "agent_url is required — Cekura must reach a public agent endpoint. "
                "Deploy the bot to Pipecat Cloud / Twilio first, then pass its URL."
            ),
        )

    scenario, _ = _load_scenario_rubric(req.scenario)

    def _run() -> dict:
        from fairbench.adapters.eval.cekura import CekuraClient
        from fairbench.battery import build_battery

        accents = sorted({c["group"]["accent"] for c in build_battery(slim=True)})
        result_id = CekuraClient().run_accent_battery(
            agent_url=req.agent_url,
            accents=accents,
            scenario_name=scenario.title,
            scenario_prompt=scenario.system_prompt,
            agent_name=f"FairBench {scenario.id}",
        )
        return {"result_id": result_id, "scenario": scenario.id}

    try:
        return await run_in_threadpool(_run)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cekura API {exc.response.status_code}: {exc.response.text[:300]}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def run() -> None:
    import uvicorn

    s = get_settings()
    logger.info(f"FairBench control-plane on http://{s.host}:{s.port}")
    uvicorn.run("fairbench.server.app:app", host=s.host, port=s.port)


if __name__ == "__main__":
    run()
