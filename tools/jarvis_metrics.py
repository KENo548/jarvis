#!/usr/bin/env python3
"""Prometheus-style metrics snapshot for JARVIS."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import memory_store


DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _scalar_count(conn: sqlite3.Connection, query: str) -> int:
    try:
        row = conn.execute(query).fetchone()
    except sqlite3.OperationalError:
        return 0
    if row is None:
        return 0
    return int(row["count"])


def _safe_rows(conn: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    try:
        return conn.execute(query).fetchall()
    except sqlite3.OperationalError:
        return []


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_metrics(db_path: Path = DB_PATH) -> str:
    conn = connect(db_path)
    try:
        lines: list[str] = []
        runtime_rows = _safe_rows(
            conn, "SELECT state, COUNT(*) AS count FROM runtime_instances GROUP BY state ORDER BY state"
        )
        for row in runtime_rows:
            lines.append(f'jarvis_runtime_instances_total{{state="{_escape_label(row["state"])}"}} {row["count"]}')

        pending_approvals = _scalar_count(
            conn, "SELECT COUNT(*) AS count FROM approval_queue WHERE status = 'pending'"
        )
        lines.append(f"jarvis_pending_approvals_total {pending_approvals}")

        capabilities_enabled = _scalar_count(
            conn, "SELECT COUNT(*) AS count FROM capability_catalog WHERE enabled = 1"
        )
        lines.append(f"jarvis_capabilities_enabled_total {capabilities_enabled}")

        lines.append(f"jarvis_chroma_available {1 if memory_store.chroma_available() else 0}")

        routing_decisions = _scalar_count(conn, "SELECT COUNT(*) AS count FROM routing_decisions")
        lines.append(f"jarvis_routing_decisions_total {routing_decisions}")

        capability_rows = _safe_rows(conn, "SELECT capability_id, success_count, total_cost FROM capability_metrics ORDER BY capability_id")
        for row in capability_rows:
            success_count = max(int(row["success_count"]), 0)
            total_cost = float(row["total_cost"])
            cost_per_success = total_cost / success_count if success_count else 0.0
            capability_id = _escape_label(row["capability_id"])
            lines.append(
                f'jarvis_capability_cost_per_success{{capability_id="{capability_id}"}} {cost_per_success}'
            )

        return "\n".join(lines) + ("\n" if lines else "")
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS metrics exporter")
    parser.add_argument("--output", help="Write metrics to this file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metrics = build_metrics()
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(metrics, encoding="utf-8")
        print(f"Wrote metrics to {output_path}")
    else:
        sys.stdout.write(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())