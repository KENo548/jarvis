#!/usr/bin/env python3
"""Initialize JARVIS SQLite database (approval queue, system control, runtimes, registry)."""

import os
import sqlite3
import sys
from pathlib import Path

from capability_registry import SCHEMA as REGISTRY_SCHEMA
from runtime_lifecycle import SCHEMA as RUNTIME_SCHEMA

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

FULL_SCHEMA = SCHEMA + "\n" + RUNTIME_SCHEMA
FULL_SCHEMA = FULL_SCHEMA + "\n" + REGISTRY_SCHEMA


def main() -> int:
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.executescript(FULL_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    print(f"[OK] SQLite database initialized: {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
