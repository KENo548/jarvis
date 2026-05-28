"""Capture and analyze user behavioral signals for the SAGE AI ecosystem."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .interaction_logger import _connect

SIGNAL_TYPES = frozenset(
    {
        "immediate_reuse",
        "edited_output",
        "re_prompted",
        "abandoned",
        "repeated_retries",
        "approval_override",
        "ignored_output",
    }
)

SIGNAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS behavioral_signals (
    signal_id TEXT PRIMARY KEY,
    session_id TEXT,
    interaction_id TEXT,
    signal_type TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL
);
"""


def init_signals_table(db_path: Optional[str | Path] = None) -> None:
    """Ensure the behavioral_signals table exists."""
    conn = _connect(db_path)
    try:
        conn.executescript(SIGNAL_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def log_signal(
    session_id: str,
    interaction_id: str,
    signal_type: str,
    details: str = "",
    db_path: Optional[str | Path] = None,
) -> str:
    """Log a behavioral signal and return its signal_id."""
    if signal_type not in SIGNAL_TYPES:
        raise ValueError(f"signal_type must be one of {SIGNAL_TYPES}, got {signal_type!r}")

    signal_id = f"sig_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    conn = _connect(db_path)
    try:
        conn.executescript(SIGNAL_SCHEMA)
        conn.execute(
            """INSERT INTO behavioral_signals
               (signal_id, session_id, interaction_id, signal_type, details, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (signal_id, session_id, interaction_id, signal_type, json.dumps(details) if isinstance(details, dict) else details, now),
        )
        conn.commit()
    finally:
        conn.close()
    return signal_id


def get_signals(
    session_id: str | None = None,
    limit: int = 50,
    db_path: Optional[str | Path] = None,
) -> list[dict[str, Any]]:
    """Query signals, optionally filtered by session."""
    conn = _connect(db_path)
    try:
        conn.executescript(SIGNAL_SCHEMA)
        if session_id:
            rows = conn.execute(
                "SELECT * FROM behavioral_signals WHERE session_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM behavioral_signals ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_signal_summary(db_path: Optional[str | Path] = None) -> dict[str, Any]:
    """Count signals by type and return a summary dict."""
    conn = _connect(db_path)
    try:
        conn.executescript(SIGNAL_SCHEMA)
        rows = conn.execute(
            "SELECT signal_type, COUNT(*) as cnt FROM behavioral_signals "
            "GROUP BY signal_type ORDER BY cnt DESC"
        ).fetchall()
        by_type = {r["signal_type"]: r["cnt"] for r in rows}
        total = sum(by_type.values())

        recent = conn.execute(
            "SELECT signal_type, details FROM behavioral_signals "
            "ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()
        recent_details = [
            {"type": r["signal_type"], "details": r["details"]} for r in recent
        ]

        return {
            "total_signals": total,
            "by_type": by_type,
            "recent_signals": recent_details,
        }
    finally:
        conn.close()


def detect_failure_patterns(db_path: Optional[str | Path] = None) -> list[dict[str, Any]]:
    """Detect recurring failure patterns from behavioral signals.

    Patterns detected:
    - Repeated re-prompts (3+) on the same interaction (topic)
    - Abandoned interactions
    - High retry sequences
    """
    conn = _connect(db_path)
    try:
        conn.executescript(SIGNAL_SCHEMA)
        patterns: list[dict[str, Any]] = []

        re_prompt_groups = conn.execute(
            """SELECT interaction_id, COUNT(*) as cnt
               FROM behavioral_signals
               WHERE signal_type = 're_prompted'
               GROUP BY interaction_id
               HAVING cnt >= 3"""
        ).fetchall()
        for g in re_prompt_groups:
            patterns.append(
                {
                    "pattern": "repeated_re_prompts",
                    "interaction_id": g["interaction_id"],
                    "count": g["cnt"],
                    "severity": "high" if g["cnt"] >= 5 else "medium",
                    "suggestion": "Consider revising the initial prompt or agent routing.",
                }
            )

        abandoned = conn.execute(
            """SELECT interaction_id, COUNT(*) as cnt
               FROM behavioral_signals
               WHERE signal_type = 'abandoned'
               GROUP BY interaction_id
               HAVING cnt >= 1"""
        ).fetchall()
        for a in abandoned:
            patterns.append(
                {
                    "pattern": "abandoned_interaction",
                    "interaction_id": a["interaction_id"],
                    "count": a["cnt"],
                    "severity": "medium",
                    "suggestion": "Investigate why the user abandoned this interaction.",
                }
            )

        retry_groups = conn.execute(
            """SELECT interaction_id, COUNT(*) as cnt
               FROM behavioral_signals
               WHERE signal_type = 'repeated_retries'
               GROUP BY interaction_id
               HAVING cnt >= 2"""
        ).fetchall()
        for r in retry_groups:
            patterns.append(
                {
                    "pattern": "excessive_retries",
                    "interaction_id": r["interaction_id"],
                    "count": r["cnt"],
                    "severity": "high",
                    "suggestion": "Tool or agent may be failing repeatedly.",
                }
            )

        edit_heavy = conn.execute(
            """SELECT interaction_id, COUNT(*) as cnt
               FROM behavioral_signals
               WHERE signal_type = 'edited_output'
               GROUP BY interaction_id
               HAVING cnt >= 3"""
        ).fetchall()
        for e in edit_heavy:
            patterns.append(
                {
                    "pattern": "frequent_edits",
                    "interaction_id": e["interaction_id"],
                    "count": e["cnt"],
                    "severity": "medium",
                    "suggestion": "Agent output quality may need improvement.",
                }
            )

        return patterns
    finally:
        conn.close()
