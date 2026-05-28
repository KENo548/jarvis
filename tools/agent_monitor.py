#!/usr/bin/env python3
"""
JARVIS Self-Monitoring — Agent Health & Error Detection
========================================================
Monitors agent activity, detects errors, anomalies, and stalled tasks.
Agents can call this to flag their own issues.

Usage:
    python tools/agent_monitor.py status          # Current agent health
    python tools/agent_monitor.py errors          # Recent errors
    python tools/agent_monitor.py health          # Full health report
    python tools/agent_monitor.py check-kill      # Check if kill switch is active
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"
AUDIT_LOG = Path(__file__).resolve().parent.parent / "logs" / "audit.log"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def check_kill_switch() -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT value FROM system_control WHERE key = 'kill_switch'"
        ).fetchone()
        conn.close()
        if row and row["value"] == "true":
            return {"active": True, "message": "KILL SWITCH IS ACTIVE — all agents halted"}
        return {"active": False, "message": "Kill switch inactive — agents operational"}
    except sqlite3.OperationalError:
        conn.close()
        return {"active": False, "message": "No system_control table — kill switch not initialized"}


def get_pending_approvals() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, timestamp, agent_id, action_type, action_detail, risk_level "
        "FROM approval_queue WHERE status = 'pending' ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_errors(limit: int = 20) -> list[dict]:
    errors = []
    if AUDIT_LOG.exists():
        lines = AUDIT_LOG.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(lines[-200:]):
            try:
                entry = json.loads(line)
                if entry.get("event_type") in ("error", "agent_error", "failed"):
                    errors.append(entry)
                    if len(errors) >= limit:
                        break
            except json.JSONDecodeError:
                continue
    return errors


def get_agent_activity_summary() -> dict:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT agent_id, action_type, status, COUNT(*) as count "
            "FROM approval_history "
            "GROUP BY agent_id, action_type, status "
            "ORDER BY count DESC"
        ).fetchall()
        conn.close()

        agents = {}
        for r in rows:
            agent = r["agent_id"]
            if agent not in agents:
                agents[agent] = {"actions": 0, "approved": 0, "rejected": 0}
            agents[agent]["actions"] += r["count"]
            if r["status"] == "approved":
                agents[agent]["approved"] += r["count"]
            elif r["status"] == "rejected":
                agents[agent]["rejected"] += r["count"]
        return agents
    except sqlite3.OperationalError:
        conn.close()
        return {}


def health_report() -> dict:
    kill = check_kill_switch()
    pending = get_pending_approvals()
    errors = get_recent_errors()
    activity = get_agent_activity_summary()

    health_score = 100
    issues = []

    if kill["active"]:
        health_score -= 50
        issues.append("Kill switch is active")

    if len(pending) > 10:
        health_score -= 20
        issues.append(f"{len(pending)} pending approvals (backlog)")

    if len(errors) > 5:
        health_score -= 15
        issues.append(f"{len(errors)} recent errors in audit log")

    if not activity:
        health_score -= 10
        issues.append("No agent activity recorded")

    health_score = max(0, health_score)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health_score": health_score,
        "kill_switch": kill,
        "pending_approvals": len(pending),
        "recent_errors": len(errors),
        "agent_activity": activity,
        "issues": issues,
        "verdict": "HEALTHY" if health_score >= 80 else "DEGRADED" if health_score >= 50 else "CRITICAL",
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "status":
        kill = check_kill_switch()
        pending = get_pending_approvals()
        print(f"Kill switch: {'ACTIVE' if kill['active'] else 'inactive'}")
        print(f"Pending approvals: {len(pending)}")
        for p in pending[:5]:
            print(f"  [{p['id']}] {p['agent_id']} — {p['action_type']}: {p['action_detail'][:60]}")

    elif cmd == "errors":
        errors = get_recent_errors()
        if not errors:
            print("No recent errors.")
        for e in errors:
            print(f"  [{e.get('timestamp', '?')}] {e.get('event_type', '?')}: {e.get('detail', '?')[:80]}")

    elif cmd == "health":
        report = health_report()
        print(json.dumps(report, indent=2))

    elif cmd == "check-kill":
        kill = check_kill_switch()
        print(json.dumps(kill))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
