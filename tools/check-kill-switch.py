#!/usr/bin/env python3
"""
Check kill switch status and show system health summary.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"


def main():
    if not DB_PATH.exists():
        print("Database not initialized yet. Run: python tools/approval-queue.py list")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Kill switch status
    row = conn.execute(
        "SELECT value, updated_at FROM system_control WHERE key = 'kill_switch'"
    ).fetchone()
    if row:
        status = "ACTIVE (agents stopped)" if row["value"] == "true" else "INACTIVE (agents can run)"
        print(f"Kill Switch: {status}")
        print(f"  Last updated: {row['updated_at']}")
    else:
        print("Kill Switch: NOT CONFIGURED")

    # Pending approvals
    pending = conn.execute(
        "SELECT COUNT(*) FROM approval_queue WHERE status = 'pending'"
    ).fetchone()[0]
    print(f"Pending Approvals: {pending}")

    # Recent activity
    recent = conn.execute(
        "SELECT COUNT(*) FROM approval_history WHERE approved_at > datetime('now', '-24 hours')"
    ).fetchone()[0]
    print(f"Actions (last 24h): {recent}")

    # Schema version
    version = conn.execute(
        "SELECT value FROM system_control WHERE key = 'schema_version'"
    ).fetchone()
    if version:
        print(f"Schema Version: {version['value']}")

    conn.close()


if __name__ == "__main__":
    main()
