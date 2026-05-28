#!/usr/bin/env python3
"""
JARVIS Kill Switch Reset — Re-enable agents after emergency stop.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.execute(
        "SELECT value FROM system_control WHERE key = 'kill_switch' AND value = 'true'"
    )
    row = cur.fetchone()

    if not row:
        print("Kill switch is not active. No action needed.")
        conn.close()
        return

    conn.execute(
        "UPDATE system_control SET value = 'false', updated_at = ? WHERE key = 'kill_switch'",
        (datetime.now(timezone.utc).isoformat(),)
    )
    conn.commit()
    conn.close()

    print("Kill switch deactivated. Agents can now accept tasks again.")
    print("If any agents were manually stopped, restart them now.")


if __name__ == "__main__":
    main()
