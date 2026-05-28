#!/usr/bin/env python3
"""
JARVIS Approval Queue — Human-in-the-Loop Gate
================================================
All agent actions that modify state go through this queue.
You see a summary: what the agent wants to do, why, and the estimated impact.
You approve or reject. Nothing gets executed without your sign-off.

Usage:
    python approval-queue.py list              # Show pending approvals
    python approval-queue.py approve <id>      # Approve an action
    python approval-queue.py reject <id>       # Reject an action
    python approval-queue.py history           # Show recent decisions
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"


def get_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
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
        )
    """)
    conn.execute("""
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
        )
    """)
    conn.commit()
    return conn


def list_pending():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, timestamp, agent_id, action_type, action_detail, risk_level "
        "FROM approval_queue WHERE status = 'pending' ORDER BY id ASC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No pending approvals.")
        return

    print(f"{'ID':<5} {'Time':<22} {'Agent':<18} {'Type':<20} {'Risk':<10} Detail")
    print("-" * 100)
    for r in rows:
        detail = r["action_detail"][:50] + "..." if len(r["action_detail"]) > 50 else r["action_detail"]
        print(f"{r['id']:<5} {r['timestamp']:<22} {r['agent_id']:<18} {r['action_type']:<20} {r['risk_level']:<10} {detail}")


def approve(action_id, approver="human"):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM approval_queue WHERE id = ? AND status = 'pending'",
        (action_id,)
    ).fetchone()

    if not row:
        print(f"Error: No pending action with id {action_id}")
        conn.close()
        return False

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE approval_queue SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
        (approver, now, action_id)
    )
    conn.execute(
        "INSERT INTO approval_history (timestamp, agent_id, action_type, action_detail, risk_level, status, approved_by, approved_at) "
        "VALUES (?, ?, ?, ?, ?, 'approved', ?, ?)",
        (row["timestamp"], row["agent_id"], row["action_type"], row["action_detail"],
         row["risk_level"], approver, now)
    )
    conn.commit()
    conn.close()

    print(f"Approved action {action_id}.")
    return True


def reject(action_id, reason="Rejected by human"):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM approval_queue WHERE id = ? AND status = 'pending'",
        (action_id,)
    ).fetchone()

    if not row:
        print(f"Error: No pending action with id {action_id}")
        conn.close()
        return False

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE approval_queue SET status = 'rejected', rejection_reason = ?, approved_at = ? WHERE id = ?",
        (reason, now, action_id)
    )
    conn.execute(
        "INSERT INTO approval_history (timestamp, agent_id, action_type, action_detail, risk_level, status, rejection_reason, approved_at) "
        "VALUES (?, ?, ?, ?, ?, 'rejected', ?, ?)",
        (row["timestamp"], row["agent_id"], row["action_type"], row["action_detail"],
         row["risk_level"], reason, now)
    )
    conn.commit()
    conn.close()

    print(f"Rejected action {action_id}: {reason}")
    return True


def enqueue(agent_id, action_type, action_detail, risk_level="medium", inputs_hash=None):
    """Called by agents to queue an action for approval."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO approval_queue (timestamp, agent_id, action_type, action_detail, inputs_hash, risk_level) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (now, agent_id, action_type, action_detail, inputs_hash, risk_level)
    )
    conn.commit()
    conn.close()
    print(f"[QUEUED] {agent_id} — {action_type} — {action_detail[:60]}")
    return True


def history(limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT timestamp, agent_id, action_type, action_detail, risk_level, status, approved_by "
        "FROM approval_history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()

    if not rows:
        print("No approval history.")
        return

    print(f"{'Time':<22} {'Agent':<18} {'Type':<20} {'Risk':<8} {'Status':<12} Approved By")
    print("-" * 100)
    for r in rows:
        print(f"{r['timestamp']:<22} {r['agent_id']:<18} {r['action_type']:<20} {r['risk_level']:<8} {r['status']:<12} {r['approved_by'] or '-'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python approval-queue.py list")
        print("  python approval-queue.py approve <id>")
        print("  python approval-queue.py reject <id> [reason]")
        print("  python approval-queue.py history [limit]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        list_pending()
    elif command == "approve" and len(sys.argv) >= 3:
        approve(int(sys.argv[2]))
    elif command == "reject" and len(sys.argv) >= 3:
        reason = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "Rejected by human"
        reject(int(sys.argv[2]), reason)
    elif command == "history":
        limit = int(sys.argv[2]) if len(sys.argv) >= 3 else 20
        history(limit)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
