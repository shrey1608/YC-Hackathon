"""Persist synthetic session transcripts for grading and audit."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def sessions_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    d = root / ".sessions"
    d.mkdir(exist_ok=True)
    return d


def save_session(
    scenario_id: str,
    turns: list[dict],
    metadata: dict | None = None,
    session_id: str | None = None,
) -> str:
    sid = session_id or f"syn-{uuid4().hex[:8]}"
    payload = {
        "session_id": sid,
        "scenario_id": scenario_id,
        "created_at": datetime.now(UTC).isoformat(),
        "synthetic_only": True,
        "turns": turns,
        "metadata": metadata or {},
    }
    path = sessions_dir() / f"{sid}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sid


def load_session(session_id: str) -> dict:
    path = sessions_dir() / f"{session_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions() -> list[Path]:
    return sorted(sessions_dir().glob("syn-*.json"))
