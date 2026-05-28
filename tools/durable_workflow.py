from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "workflows.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,
    input_json TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
);

CREATE TABLE IF NOT EXISTS workflow_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    error_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
);
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


@dataclass
class WorkflowRun:
    run_id: str
    workflow_type: str
    input_json: str
    state: str
    result_json: str | None
    error: str | None
    retry_count: int
    max_retries: int
    created_at: str
    updated_at: str
    started_at: str | None
    completed_at: str | None
    steps: list[dict[str, Any]] = field(default_factory=list)


def _row_to_run(row: sqlite3.Row) -> WorkflowRun:
    return WorkflowRun(
        run_id=row["run_id"],
        workflow_type=row["workflow_type"],
        input_json=row["input_json"],
        state=row["state"],
        result_json=row["result_json"],
        error=row["error"],
        retry_count=row["retry_count"],
        max_retries=row["max_retries"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


def create_run(
    workflow_type: str,
    input_data: dict[str, Any],
    max_retries: int = 3,
    db_path: Path = DB_PATH,
) -> WorkflowRun:
    conn = connect(db_path)
    try:
        run_id = str(uuid.uuid4())
        now = now_iso()
        conn.execute(
            """INSERT INTO workflow_runs
               (run_id, workflow_type, input_json, state, max_retries, created_at, updated_at)
               VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
            (run_id, workflow_type, json.dumps(input_data, sort_keys=True), max_retries, now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
        return _row_to_run(row)
    finally:
        conn.close()


def get_run(run_id: str, db_path: Path = DB_PATH) -> WorkflowRun | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        run = _row_to_run(row)
        run.steps = [
            dict(s) for s in conn.execute(
                "SELECT * FROM workflow_steps WHERE run_id = ? ORDER BY step_id ASC", (run_id,)
            ).fetchall()
        ]
        return run
    finally:
        conn.close()


def list_runs(limit: int = 20, db_path: Path = DB_PATH) -> list[WorkflowRun]:
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_run(r) for r in rows]
    finally:
        conn.close()


def _backoff_delay(attempt: int, base: float = 1.0, max_delay: float = 60.0) -> float:
    return min(base * (2 ** (attempt - 1)) + (attempt - 1) * 0.5, max_delay)


def execute_workflow(
    workflow_type: str,
    input_data: dict[str, Any],
    steps: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]],
    max_retries: int = 3,
    db_path: Path = DB_PATH,
) -> WorkflowRun:
    run = create_run(workflow_type, input_data, max_retries=max_retries, db_path=db_path)
    conn = connect(db_path)

    try:
        now = now_iso()
        conn.execute(
            "UPDATE workflow_runs SET state = 'running', started_at = ?, updated_at = ? WHERE run_id = ?",
            (now, now, run.run_id),
        )
        conn.commit()

        accumulated_input = dict(input_data)

        for step_name, step_fn in steps:
            attempt = 0
            last_error: str | None = None

            while attempt <= max_retries:
                attempt += 1
                step_start = now_iso()
                try:
                    conn.execute(
                        """INSERT INTO workflow_steps (run_id, step_name, state, started_at)
                           VALUES (?, ?, 'running', ?)""",
                        (run.run_id, step_name, step_start),
                    )
                    step_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                    result = step_fn(accumulated_input)

                    conn.execute(
                        "UPDATE workflow_steps SET state = 'completed', result_json = ?, completed_at = ? WHERE step_id = ?",
                        (json.dumps(result, sort_keys=True), now_iso(), step_id),
                    )
                    conn.execute(
                        "UPDATE workflow_runs SET updated_at = ? WHERE run_id = ?",
                        (now_iso(), run.run_id),
                    )
                    conn.commit()

                    result.setdefault("step_name", step_name)
                    accumulated_input[f"_{step_name}_result"] = result
                    last_error = None
                    break

                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    now_iso()
                    conn.execute(
                        "UPDATE workflow_steps SET state = 'failed', error = ?, completed_at = ? WHERE step_id = ?",
                        (last_error, now_iso(), conn.execute("SELECT last_insert_rowid()").fetchone()[0]),
                    ) if attempt == 1 else None

                    conn.execute(
                        "INSERT INTO workflow_errors (run_id, step_name, attempt, error_text, created_at) VALUES (?, ?, ?, ?, ?)",
                        (run.run_id, step_name, attempt, last_error, now_iso()),
                    )
                    conn.commit()

                    now_iso()
                    conn.execute(
                        "UPDATE workflow_runs SET retry_count = ?, updated_at = ? WHERE run_id = ?",
                        (attempt, now_iso(), run.run_id),
                    )
                    conn.commit()

                    if attempt <= max_retries:
                        delay = _backoff_delay(attempt)
                        time.sleep(delay)

            if last_error is not None:
                now = now_iso()
                conn.execute(
                    "UPDATE workflow_runs SET state = 'failed', error = ?, completed_at = ?, updated_at = ? WHERE run_id = ?",
                    (last_error, now, now, run.run_id),
                )
                conn.commit()
                conn.close()
                return get_run(run.run_id, db_path=db_path)

        now = now_iso()
        conn.execute(
            "UPDATE workflow_runs SET state = 'completed', result_json = ?, completed_at = ?, updated_at = ? WHERE run_id = ?",
            (json.dumps(accumulated_input, sort_keys=True), now, now, run.run_id),
        )
        conn.commit()
    finally:
        conn.close()

    return get_run(run.run_id, db_path=db_path)


def retry_failed_run(run_id: str, db_path: Path = DB_PATH) -> WorkflowRun | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None or row["state"] != "failed":
            return None

        conn.execute(
            "UPDATE workflow_runs SET state = 'pending', retry_count = 0, error = NULL, updated_at = ? WHERE run_id = ?",
            (now_iso(), run_id),
        )
        conn.execute("DELETE FROM workflow_steps WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM workflow_errors WHERE run_id = ?", (run_id,))
        conn.commit()
        return get_run(run_id, db_path=db_path)
    finally:
        conn.close()
