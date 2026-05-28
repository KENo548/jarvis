#!/usr/bin/env python3
"""Shared governance helpers for JARVIS approvals and kill switch state."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import audit_log

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT NOT NULL,
    inputs_hash TEXT,
    risk_level TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    approved_by TEXT,
    approved_at TEXT,
    rejection_reason TEXT,
    auto_executed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS approval_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,
    approved_by TEXT,
    approved_at TEXT,
    rejection_reason TEXT,
    auto_executed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS system_control (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);

INSERT OR IGNORE INTO system_control (key, value, updated_at)
    VALUES ('kill_switch', 'false', datetime('now'));
INSERT OR IGNORE INTO system_control (key, value, updated_at)
    VALUES ('schema_version', '1.0.0', datetime('now'));
INSERT OR IGNORE INTO system_control (key, value, updated_at)
    VALUES ('system_status', 'initialized', datetime('now'));
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def is_kill_switch_active(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT value FROM system_control WHERE key = 'kill_switch'").fetchone()
    return bool(row and row["value"] == "true")


def require_kill_switch_open(conn: sqlite3.Connection) -> None:
    if is_kill_switch_active(conn):
        raise PermissionError("Kill switch is active; runtime actions are blocked")


def enqueue_approval(
    agent_id: str,
    action_type: str,
    action_detail: str,
    risk_level: str = "medium",
    inputs_hash: str | None = None,
    db_path: Path = DB_PATH,
) -> int:
    conn = connect(db_path)
    try:
        now = now_iso()
        cur = conn.execute(
            "INSERT INTO approval_queue (timestamp, agent_id, action_type, action_detail, inputs_hash, risk_level) VALUES (?, ?, ?, ?, ?, ?)",
            (now, agent_id, action_type, action_detail, inputs_hash, risk_level),
        )
        conn.commit()
        audit_log.append_entry(
            "approval_queued",
            f"Queued {action_type} for {agent_id}",
            agent_id=agent_id,
            action_type=action_type,
            action_detail=action_detail,
            risk_level=risk_level,
            approval_id=int(cur.lastrowid),
        )
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_approval(action_id: int, db_path: Path = DB_PATH) -> sqlite3.Row | None:
    conn = connect(db_path)
    try:
        return conn.execute("SELECT * FROM approval_queue WHERE id = ?", (action_id,)).fetchone()
    finally:
        conn.close()


def is_approved(action_id: int, db_path: Path = DB_PATH) -> bool:
    row = get_approval(action_id, db_path=db_path)
    return bool(row and row["status"] == "approved")


def approve_action(action_id: int, approver: str = "human", db_path: Path = DB_PATH) -> bool:
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM approval_queue WHERE id = ? AND status = 'pending'",
            (action_id,),
        ).fetchone()
        if row is None:
            return False

        now = now_iso()
        conn.execute(
            "UPDATE approval_queue SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
            (approver, now, action_id),
        )
        conn.execute(
            "INSERT INTO approval_history (timestamp, agent_id, action_type, action_detail, risk_level, status, approved_by, approved_at) VALUES (?, ?, ?, ?, ?, 'approved', ?, ?)",
            (row["timestamp"], row["agent_id"], row["action_type"], row["action_detail"], row["risk_level"], approver, now),
        )
        conn.commit()
        audit_log.append_entry(
            "approval_approved",
            f"Approved {row['action_type']} for {row['agent_id']}",
            approval_id=action_id,
            approver=approver,
            agent_id=row["agent_id"],
            action_type=row["action_type"],
            action_detail=row["action_detail"],
            risk_level=row["risk_level"],
        )
        return True
    finally:
        conn.close()


def reject_action(action_id: int, reason: str = "Rejected by human", db_path: Path = DB_PATH) -> bool:
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM approval_queue WHERE id = ? AND status = 'pending'",
            (action_id,),
        ).fetchone()
        if row is None:
            return False

        now = now_iso()
        conn.execute(
            "UPDATE approval_queue SET status = 'rejected', rejection_reason = ?, approved_at = ? WHERE id = ?",
            (reason, now, action_id),
        )
        conn.execute(
            "INSERT INTO approval_history (timestamp, agent_id, action_type, action_detail, risk_level, status, rejection_reason, approved_at) VALUES (?, ?, ?, ?, ?, 'rejected', ?, ?)",
            (row["timestamp"], row["agent_id"], row["action_type"], row["action_detail"], row["risk_level"], reason, now),
        )
        conn.commit()
        audit_log.append_entry(
            "approval_rejected",
            f"Rejected {row['action_type']} for {row['agent_id']}",
            approval_id=action_id,
            reason=reason,
            agent_id=row["agent_id"],
            action_type=row["action_type"],
            action_detail=row["action_detail"],
            risk_level=row["risk_level"],
        )
        return True
    finally:
        conn.close()


def require_approval(
    agent_id: str,
    action_type: str,
    action_detail: str,
    risk_level: str = "medium",
    inputs_hash: str | None = None,
    approval_id: int | None = None,
    db_path: Path = DB_PATH,
) -> int:
    if approval_id is None:
        queued_id = enqueue_approval(
            agent_id=agent_id,
            action_type=action_type,
            action_detail=action_detail,
            risk_level=risk_level,
            inputs_hash=inputs_hash,
            db_path=db_path,
        )
        raise PermissionError(f"Approval required; queued action {queued_id}")

    if not is_approved(approval_id, db_path=db_path):
        raise PermissionError(f"Approval {approval_id} is not approved")

    return approval_id


def set_kill_switch(active: bool, db_path: Path = DB_PATH) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            "UPDATE system_control SET value = ?, updated_at = ? WHERE key = 'kill_switch'",
            ("true" if active else "false", now_iso()),
        )
        conn.commit()
    finally:
        conn.close()
