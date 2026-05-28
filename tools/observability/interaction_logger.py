"""SQLite-based interaction logging for SAGE AI ecosystem."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB = Path(r"C:\jarvis\memory\sqlite\interactions.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS interactions (
    interaction_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    workflow_id TEXT,
    timestamp TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    model_name TEXT,
    input_text TEXT,
    assembled_context TEXT,
    retrieved_memories TEXT,
    tool_calls TEXT,
    tool_outputs TEXT,
    reasoning_trace TEXT,
    output_text TEXT,
    latency_ms INTEGER,
    token_usage TEXT,
    auto_eval TEXT,
    human_feedback TEXT,
    correction TEXT,
    retry_count INTEGER DEFAULT 0,
    was_edited INTEGER DEFAULT 0,
    was_abandoned INTEGER DEFAULT 0,
    followup_prompt TEXT,
    success_score REAL DEFAULT 0.0,
    domain TEXT DEFAULT 'general',
    created_at TEXT NOT NULL
);
"""


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    p = Path(db_path) if db_path else DEFAULT_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Optional[str | Path] = None) -> None:
    """Create the interactions table if it does not exist."""
    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def log_interaction(
    agent_name: str,
    input_text: str,
    output_text: str,
    model: str = "",
    duration_ms: int = 0,
    session_id: str = "",
    task_id: str = "",
    memory_context_snapshot: str = "",
    tool_calls_made: list[dict[str, Any]] | None = None,
    reasoning_trace: str = "",
    quality: str = "",
    correction: str = "",
    domain: str = "general",
    db_path: Optional[str | Path] = None,
) -> str:
    """Insert a new interaction row and return its interaction_id."""
    interaction_id = f"int_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    conn = _connect(db_path)
    try:
        conn.execute(
            """INSERT INTO interactions
               (interaction_id, session_id, workflow_id, timestamp, agent_name,
                model_name, input_text, assembled_context, retrieved_memories,
                tool_calls, tool_outputs, reasoning_trace, output_text,
                latency_ms, token_usage, auto_eval, human_feedback,
                correction, retry_count, was_edited, was_abandoned,
                followup_prompt, success_score, domain, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                interaction_id,
                session_id,
                task_id,
                now,
                agent_name,
                model,
                input_text,
                json.dumps(memory_context_snapshot) if isinstance(memory_context_snapshot, dict) else memory_context_snapshot,
                json.dumps([]),
                json.dumps(tool_calls_made or []),
                json.dumps([]),
                reasoning_trace,
                output_text,
                duration_ms,
                json.dumps({}),
                json.dumps({}),
                json.dumps({}),
                correction,
                0,
                0,
                0,
                "",
                0.0,
                domain,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return interaction_id


def get_interaction(
    interaction_id: str, db_path: Optional[str | Path] = None
) -> dict[str, Any] | None:
    """Fetch a single interaction by id."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM interactions WHERE interaction_id = ?",
            (interaction_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_recent_interactions(
    limit: int = 10,
    agent_name: str | None = None,
    domain: str | None = None,
    db_path: Optional[str | Path] = None,
) -> list[dict[str, Any]]:
    """Query recent interactions with optional filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if agent_name:
        clauses.append("agent_name = ?")
        params.append(agent_name)
    if domain:
        clauses.append("domain = ?")
        params.append(domain)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM interactions{where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_stats(db_path: Optional[str | Path] = None) -> dict[str, Any]:
    """Return aggregate statistics across all logged interactions."""
    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        avg_latency = cur.execute(
            "SELECT AVG(latency_ms) FROM interactions WHERE latency_ms > 0"
        ).fetchone()[0]
        avg_tokens = cur.execute(
            "SELECT AVG(CAST(json_extract(token_usage, '$.total') AS REAL)) "
            "FROM interactions WHERE token_usage != '{}'"
        ).fetchone()[0]

        by_agent = {
            row[0]: row[1]
            for row in cur.execute(
                "SELECT agent_name, COUNT(*) FROM interactions GROUP BY agent_name"
            ).fetchall()
        }
        by_domain = {
            row[0]: row[1]
            for row in cur.execute(
                "SELECT domain, COUNT(*) FROM interactions GROUP BY domain"
            ).fetchall()
        }
        return {
            "total_interactions": total,
            "avg_latency_ms": round(avg_latency or 0, 2),
            "avg_tokens": round(avg_tokens or 0, 2),
            "by_agent": by_agent,
            "by_domain": by_domain,
        }
    finally:
        conn.close()
