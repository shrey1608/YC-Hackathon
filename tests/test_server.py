"""
Light smoke tests for the FastAPI control-plane.

No network and no real voice: Cekura is gated by key (asserted 503), and the
WebRTC offer handler is monkeypatched so /api/offer never opens a peer
connection or starts the bot. Keeps the existing offline suite untouched.
"""

from __future__ import annotations

import types

from fastapi.testclient import TestClient

from fairbench.server import app as app_module

client = TestClient(app_module.app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_scenarios_lists_known() -> None:
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()}
    assert {
        "pharmacy_tech_metformin",
        "nursing_sbar_handoff",
        "hiring_phone_screen",
    } <= ids


def test_audit_run_small() -> None:
    r = client.post(
        "/api/audit/run",
        json={"scenario": "pharmacy_tech_metformin", "per_cell": 2},
    )
    assert r.status_code == 200
    body = r.json()
    assert "verdict" in body
    assert "fairness" in body
    assert body["scenario"] == "pharmacy_tech_metformin"


def test_sessions_grade_roundtrip() -> None:
    turns = [
        {"role": "patient", "text": "I'm picking up metformin."},
        {
            "role": "trainee",
            "text": (
                "Let me verify your prescription and check your Rx. I'll ask the "
                "pharmacist about taking it with food before you go."
            ),
        },
    ]
    r = client.post(
        "/api/sessions/grade",
        json={"scenario_id": "pharmacy_tech_metformin", "turns": turns},
    )
    assert r.status_code == 200
    body = r.json()
    sid = body["session_id"]
    assert body["grade"]["scenario_id"] == "pharmacy_tech_metformin"

    listing = client.get("/api/sessions").json()
    assert any(s["session_id"] == sid for s in listing)

    detail = client.get(f"/api/sessions/{sid}").json()
    assert len(detail["turns"]) == 2


def test_feedback_returns_next_action() -> None:
    turns = [
        {"role": "patient", "text": "I'm picking up metformin."},
        {"role": "trainee", "text": "Let me verify your prescription first."},
    ]
    r = client.post(
        "/api/feedback",
        json={"scenario_id": "pharmacy_tech_metformin", "turns": turns},
    )
    assert r.status_code == 200
    body = r.json()
    assert "verify_prescription" in body["met"]
    assert body["unmet"]  # still has competencies to cover
    assert body["hint"]  # a single next action
    assert 0.0 <= body["overall"] <= 1.0


def test_audit_compare_closes_grader_axis() -> None:
    r = client.post(
        "/api/audit/compare",
        json={"scenario": "pharmacy_tech_metformin", "per_cell": 8},
    )
    assert r.status_code == 200
    body = r.json()
    assert {"before", "after", "summary"} <= set(body)
    s = body["summary"]
    by = s["by_attribute"]
    assert {"accent", "gender", "name_origin"} <= set(by)
    # De-biasing the grader clears name-origin flags but leaves the ASR-driven
    # accent flags in place — proof the attribution is real.
    assert by["name_origin"]["flagged_after"] <= by["name_origin"]["flagged_before"]
    assert by["accent"]["flagged_after"] >= 1


def test_cekura_battery_estimate() -> None:
    r = client.get(
        "/api/cekura/battery/estimate",
        params={"scenario": "pharmacy_tech_metformin"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"] == "pharmacy_tech_metformin"
    assert body["per_cell"] >= 6
    assert body["expected_calls"] == 120 * body["per_cell"]


def test_cekura_battery_runs_offline() -> None:
    r = client.get(
        "/api/cekura/battery",
        params={"scenario": "pharmacy_tech_metformin"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "matched_battery"
    assert body["verdict"]
    assert body["n_performances"] == body["expected_calls"]


def test_cekura_result_gated_without_key(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module, "get_settings", lambda: types.SimpleNamespace(cekura_api_key="")
    )
    r = client.get("/api/cekura/result/123")
    assert r.status_code == 503


def test_offer_monkeypatched(monkeypatch) -> None:
    from pipecat.transports.smallwebrtc.request_handler import (
        SmallWebRTCRequestHandler,
    )

    async def fake_handle(self, **kwargs):  # noqa: ANN001 - test stub
        return {"sdp": "v=0 answer", "type": "answer", "pc_id": "test-pc"}

    monkeypatch.setattr(
        SmallWebRTCRequestHandler, "handle_web_request", fake_handle
    )
    r = client.post("/api/offer", json={"sdp": "v=0 offer", "type": "offer"})
    assert r.status_code == 200
    assert r.json()["type"] == "answer"
