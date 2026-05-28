#!/usr/bin/env python3
"""Runtime lifecycle engine for JARVIS.

Tracks deterministic state transitions, records audit events, and applies
teardown contracts for runtime instances.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import audit_log
import governance


DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"

STATES = {
    "CREATED",
    "INITIALIZED",
    "RUNNING",
    "WAITING",
    "COMPLETED",
    "TERMINATED",
    "TIMEOUT",
    "FORCE_KILL",
    "RESOURCE_CLEANUP",
}

VALID_TRANSITIONS = {
    "CREATED": {"INITIALIZED", "FORCE_KILL"},
    "INITIALIZED": {"RUNNING", "FORCE_KILL"},
    "RUNNING": {"WAITING", "COMPLETED", "TIMEOUT", "FORCE_KILL"},
    "WAITING": {"RUNNING", "FORCE_KILL"},
    "TIMEOUT": {"FORCE_KILL"},
    "FORCE_KILL": {"RESOURCE_CLEANUP"},
    "COMPLETED": {"RESOURCE_CLEANUP"},
    "RESOURCE_CLEANUP": {"TERMINATED"},
    "TERMINATED": set(),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime_instances (
    runtime_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    requested_action TEXT NOT NULL,
    state TEXT NOT NULL,
    timeout_seconds INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    terminal_reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS runtime_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    runtime_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    reason TEXT,
    details_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    detail TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS capability_metrics (
    capability_id TEXT PRIMARY KEY,
    average_token_cost REAL NOT NULL DEFAULT 0,
    average_runtime REAL NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    human_intervention_count INTEGER NOT NULL DEFAULT 0,
    validation_pass_count INTEGER NOT NULL DEFAULT 0,
    total_cost REAL NOT NULL DEFAULT 0,
    last_30d_success_rate REAL NOT NULL DEFAULT 0,
    last_30d_invocations INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class RuntimeRecord:
    runtime_id: str
    task_id: str
    capability_id: str
    agent_id: str
    requested_action: str
    state: str
    timeout_seconds: int
    started_at: str
    updated_at: str
    completed_at: str | None
    terminal_reason: str | None
    metadata_json: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    governance_conn = governance.connect(db_path)
    governance_conn.close()
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _load_record(row: sqlite3.Row | None) -> RuntimeRecord | None:
    if row is None:
        return None
    return RuntimeRecord(
        runtime_id=row["runtime_id"],
        task_id=row["task_id"],
        capability_id=row["capability_id"],
        agent_id=row["agent_id"],
        requested_action=row["requested_action"],
        state=row["state"],
        timeout_seconds=row["timeout_seconds"],
        started_at=row["started_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
        terminal_reason=row["terminal_reason"],
        metadata_json=row["metadata_json"],
    )


def _ensure_state(value: str) -> str:
    state = value.upper().strip()
    if state not in STATES:
        raise ValueError(f"Unknown state: {value}")
    return state


def _append_event(
    conn: sqlite3.Connection,
    runtime_id: str,
    event_type: str,
    from_state: str | None,
    to_state: str,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO runtime_events (
            runtime_id, timestamp, event_type, from_state, to_state, reason, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            runtime_id,
            now_iso(),
            event_type,
            from_state,
            to_state,
            reason,
            json.dumps(details or {}, sort_keys=True),
        ),
    )
    audit_log.append_entry(
        f"runtime_{event_type}",
        f"{runtime_id}: {from_state or 'NONE'} -> {to_state}",
        runtime_id=runtime_id,
        runtime_event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        details=details or {},
    )


def _append_audit(
    conn: sqlite3.Connection,
    actor_type: str,
    actor_id: str,
    action_type: str,
    detail: str,
    approved: bool = False,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (
            timestamp, actor_type, actor_id, action_type, detail, approved, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_iso(),
            actor_type,
            actor_id,
            action_type,
            detail,
            1 if approved else 0,
            json.dumps(metadata or {}, sort_keys=True),
        ),
    )
    audit_log.append_entry(
        action_type,
        detail,
        actor_type=actor_type,
        actor_id=actor_id,
        approved=approved,
        metadata=metadata or {},
    )


def create_runtime(
    task_id: str,
    capability_id: str,
    agent_id: str,
    requested_action: str,
    timeout_seconds: int = 3600,
    approval_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    db_path: Path = DB_PATH,
) -> RuntimeRecord:
    runtime_id = f"rt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    created_at = now_iso()
    conn = connect(db_path)
    try:
        governance.require_kill_switch_open(conn)
        governance.require_approval(
            agent_id=agent_id,
            action_type="create_runtime",
            action_detail=f"Create runtime {runtime_id} for {requested_action}",
            risk_level="high",
            approval_id=approval_id,
            db_path=db_path,
        )
        conn.execute(
            """
            INSERT INTO runtime_instances (
                runtime_id, task_id, capability_id, agent_id, requested_action,
                state, timeout_seconds, started_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, 'CREATED', ?, ?, ?, ?)
            """,
            (
                runtime_id,
                task_id,
                capability_id,
                agent_id,
                requested_action,
                timeout_seconds,
                created_at,
                created_at,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        _append_event(
            conn,
            runtime_id,
            "create",
            None,
            "CREATED",
            details={"task_id": task_id, "capability_id": capability_id, "agent_id": agent_id},
        )
        _append_audit(
            conn,
            "system",
            agent_id,
            "create_runtime",
            f"Created runtime {runtime_id} for {requested_action}",
            metadata={"task_id": task_id, "capability_id": capability_id},
        )
        conn.commit()
        row = conn.execute("SELECT * FROM runtime_instances WHERE runtime_id = ?", (runtime_id,)).fetchone()
        return _load_record(row)  # type: ignore[return-value]
    finally:
        conn.close()


def get_runtime(runtime_id: str, db_path: Path = DB_PATH) -> RuntimeRecord | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM runtime_instances WHERE runtime_id = ?", (runtime_id,)).fetchone()
        return _load_record(row)
    finally:
        conn.close()


def transition_runtime(
    runtime_id: str,
    new_state: str,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    agent_id: str = "runtime",
    approval_id: int | None = None,
    db_path: Path = DB_PATH,
) -> RuntimeRecord:
    target_state = _ensure_state(new_state)
    conn = connect(db_path)
    try:
        governance.require_kill_switch_open(conn)
        row = conn.execute("SELECT * FROM runtime_instances WHERE runtime_id = ?", (runtime_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown runtime_id: {runtime_id}")

        current_state = row["state"]
        allowed_states = VALID_TRANSITIONS.get(current_state, set())
        if target_state not in allowed_states:
            raise ValueError(f"Invalid transition: {current_state} -> {target_state}")

        governance.require_approval(
            agent_id=agent_id,
            action_type="runtime_transition",
            action_detail=f"{runtime_id}: {current_state} -> {target_state}",
            risk_level="high" if target_state in {"COMPLETED", "TERMINATED", "FORCE_KILL"} else "medium",
            approval_id=approval_id,
            db_path=db_path,
        )

        conn.execute(
            """
            UPDATE runtime_instances
            SET state = ?, updated_at = ?, completed_at = CASE WHEN ? IN ('COMPLETED', 'TERMINATED') THEN ? ELSE completed_at END,
                terminal_reason = CASE WHEN ? IN ('COMPLETED', 'TERMINATED') THEN COALESCE(?, terminal_reason) ELSE terminal_reason END
            WHERE runtime_id = ?
            """,
            (target_state, now_iso(), target_state, now_iso(), target_state, reason, runtime_id),
        )
        _append_event(conn, runtime_id, "transition", current_state, target_state, reason=reason, details=details)
        _append_audit(
            conn,
            "runtime",
            runtime_id,
            "transition",
            f"{current_state} -> {target_state}",
            metadata={"reason": reason, **(details or {})},
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM runtime_instances WHERE runtime_id = ?", (runtime_id,)).fetchone()
        return _load_record(updated)  # type: ignore[return-value]
    finally:
        conn.close()


def start_runtime(runtime_id: str, db_path: Path = DB_PATH) -> RuntimeRecord:
    return start_runtime_with_approval(runtime_id, approval_id=None, db_path=db_path)


def start_runtime_with_approval(
    runtime_id: str,
    approval_id: int | None,
    db_path: Path = DB_PATH,
) -> RuntimeRecord:
    transition_runtime(
        runtime_id,
        "INITIALIZED",
        reason="runtime initialization",
        details={"phase": "initialize"},
        agent_id="runtime",
        approval_id=approval_id,
        db_path=db_path,
    )
    return transition_runtime(
        runtime_id,
        "RUNNING",
        reason="runtime started",
        details={"phase": "run"},
        agent_id="runtime",
        approval_id=approval_id,
        db_path=db_path,
    )


def complete_runtime(runtime_id: str, reason: str | None = None, db_path: Path = DB_PATH) -> RuntimeRecord:
    return complete_runtime_with_approval(runtime_id, reason=reason, approval_id=None, db_path=db_path)


def complete_runtime_with_approval(
    runtime_id: str,
    reason: str | None,
    approval_id: int | None,
    db_path: Path = DB_PATH,
) -> RuntimeRecord:
    transition_runtime(runtime_id, "COMPLETED", reason=reason or "runtime completed", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    transition_runtime(runtime_id, "RESOURCE_CLEANUP", reason="post-completion teardown", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    return transition_runtime(runtime_id, "TERMINATED", reason="cleanup finished", agent_id="runtime", approval_id=approval_id, db_path=db_path)


def timeout_runtime(runtime_id: str, reason: str | None = None, db_path: Path = DB_PATH) -> RuntimeRecord:
    return timeout_runtime_with_approval(runtime_id, reason=reason, approval_id=None, db_path=db_path)


def timeout_runtime_with_approval(
    runtime_id: str,
    reason: str | None,
    approval_id: int | None,
    db_path: Path = DB_PATH,
) -> RuntimeRecord:
    transition_runtime(runtime_id, "TIMEOUT", reason=reason or "timeout reached", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    transition_runtime(runtime_id, "FORCE_KILL", reason="timeout escalation", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    transition_runtime(runtime_id, "RESOURCE_CLEANUP", reason="forced cleanup", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    return transition_runtime(runtime_id, "TERMINATED", reason="timeout cleanup finished", agent_id="runtime", approval_id=approval_id, db_path=db_path)


def force_kill_runtime(runtime_id: str, reason: str | None = None, db_path: Path = DB_PATH) -> RuntimeRecord:
    current = get_runtime(runtime_id, db_path=db_path)
    if current is None:
        raise ValueError(f"Unknown runtime_id: {runtime_id}")
    if current.state not in {"CREATED", "INITIALIZED", "RUNNING", "WAITING", "TIMEOUT"}:
        raise ValueError(f"Cannot force-kill runtime in state {current.state}")
    return force_kill_runtime_with_approval(runtime_id, reason=reason, approval_id=None, db_path=db_path)


def force_kill_runtime_with_approval(
    runtime_id: str,
    reason: str | None,
    approval_id: int | None,
    db_path: Path = DB_PATH,
) -> RuntimeRecord:
    transition_runtime(runtime_id, "FORCE_KILL", reason=reason or "forced kill", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    transition_runtime(runtime_id, "RESOURCE_CLEANUP", reason="forced cleanup", agent_id="runtime", approval_id=approval_id, db_path=db_path)
    return transition_runtime(runtime_id, "TERMINATED", reason="force-kill cleanup finished", agent_id="runtime", approval_id=approval_id, db_path=db_path)


def list_runtimes(db_path: Path = DB_PATH) -> list[RuntimeRecord]:
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM runtime_instances ORDER BY started_at DESC").fetchall()
        return [record for record in (_load_record(row) for row in rows) if record is not None]
    finally:
        conn.close()


def print_runtime(record: RuntimeRecord) -> None:
    print(
        f"{record.runtime_id:<28} {record.state:<14} {record.agent_id:<16} "
        f"{record.capability_id:<16} timeout={record.timeout_seconds:<5} task={record.task_id}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS runtime lifecycle engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new runtime record")
    create_parser.add_argument("--task-id", required=True)
    create_parser.add_argument("--capability-id", required=True)
    create_parser.add_argument("--agent-id", required=True)
    create_parser.add_argument("--requested-action", required=True)
    create_parser.add_argument("--timeout-seconds", type=int, default=3600)
    create_parser.add_argument("--approval-id", type=int)

    for name, help_text in [
        ("start", "Transition CREATED -> INITIALIZED -> RUNNING"),
        ("complete", "Mark runtime complete and tear down resources"),
        ("timeout", "Apply timeout escalation and teardown"),
        ("force-kill", "Force kill an active runtime and tear down resources"),
        ("status", "Show a single runtime"),
    ]:
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.add_argument("runtime_id")
        command_parser.add_argument("--approval-id", type=int)

    subparsers.add_parser("list", help="List all runtime instances")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "create":
        runtime = create_runtime(
            task_id=args.task_id,
            capability_id=args.capability_id,
            agent_id=args.agent_id,
            requested_action=args.requested_action,
            timeout_seconds=args.timeout_seconds,
            approval_id=args.approval_id,
        )
        print_runtime(runtime)
        return 0

    if args.command == "start":
        print_runtime(start_runtime_with_approval(args.runtime_id, args.approval_id, db_path=DB_PATH))
        return 0

    if args.command == "complete":
        print_runtime(complete_runtime_with_approval(args.runtime_id, None, args.approval_id, db_path=DB_PATH))
        return 0

    if args.command == "timeout":
        print_runtime(timeout_runtime_with_approval(args.runtime_id, None, args.approval_id, db_path=DB_PATH))
        return 0

    if args.command == "force-kill":
        print_runtime(force_kill_runtime_with_approval(args.runtime_id, None, args.approval_id, db_path=DB_PATH))
        return 0

    if args.command == "status":
        runtime = get_runtime(args.runtime_id)
        if runtime is None:
            print(f"Runtime not found: {args.runtime_id}")
            return 1
        print_runtime(runtime)
        return 0

    if args.command == "list":
        runtimes = list_runtimes()
        if not runtimes:
            print("No runtime instances.")
            return 0
        print(f"{'Runtime ID':<28} {'State':<14} {'Agent':<16} {'Capability':<16} Timeout Task")
        print("-" * 100)
        for runtime in runtimes:
            print_runtime(runtime)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())