#!/usr/bin/env python3
"""Capability registry and rule-based routing for JARVIS.

Provides a lightweight capability catalog, metric-aware routing, and a routing
decision log so the ecosystem can pick the best available capability in a
deterministic, auditable way.
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


DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS capability_catalog (
    capability_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords_json TEXT NOT NULL DEFAULT '[]',
    toolset_json TEXT NOT NULL DEFAULT '[]',
    trust_tier TEXT NOT NULL DEFAULT 'standard',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routing_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    capability_id TEXT NOT NULL,
    match_text TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routing_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    task_text TEXT NOT NULL,
    selected_capability_id TEXT NOT NULL,
    selected_rule TEXT,
    decision_factors_json TEXT NOT NULL DEFAULT '{}'
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


DEFAULT_CAPABILITIES = [
    {
        "capability_id": "coder",
        "name": "Coder Agent",
        "role": "Writes, reviews, tests, and refactors code.",
        "description": "Code generation, refactoring, testing, and implementation support.",
        "keywords": ["code", "implement", "refactor", "bug", "test", "build", "function", "api"],
        "toolset": ["filesystem-mcp", "github-mcp", "code-sandbox-mcp"],
        "trust_tier": "high",
    },
    {
        "capability_id": "researcher",
        "name": "Researcher Agent",
        "role": "Searches the web, reads docs, and summarizes findings.",
        "description": "Web research, documentation reading, and fact gathering.",
        "keywords": ["research", "compare", "documentation", "find", "learn", "web"],
        "toolset": ["browser-mcp", "search-mcp", "fetch-mcp"],
        "trust_tier": "standard",
    },
    {
        "capability_id": "planner",
        "name": "Planner Agent",
        "role": "Breaks goals into step-by-step plans with dependencies.",
        "description": "Planning, sequencing, dependency mapping, and risk assessment.",
        "keywords": ["plan", "roadmap", "sequence", "steps", "priority", "milestone"],
        "toolset": ["filesystem-mcp", "memory-mcp"],
        "trust_tier": "standard",
    },
    {
        "capability_id": "security",
        "name": "Security Agent",
        "role": "Audits code, dependencies, logs, and policy enforcement.",
        "description": "Security review, CVE checks, and policy validation.",
        "keywords": ["security", "vulnerability", "cve", "secret", "audit", "policy", "threat"],
        "toolset": ["filesystem-mcp", "fetch-mcp", "code-sandbox-mcp"],
        "trust_tier": "high",
    },
    {
        "capability_id": "qa",
        "name": "QA Agent",
        "role": "Writes and runs tests, validates outputs, and flags regressions.",
        "description": "Testing, regression detection, and output validation.",
        "keywords": ["qa", "test", "verify", "regression", "validate", "benchmark"],
        "toolset": ["filesystem-mcp", "code-sandbox-mcp", "memory-mcp"],
        "trust_tier": "high",
    },
    {
        "capability_id": "writer",
        "name": "Writer Agent",
        "role": "Drafts documentation, READMEs, changelogs, and reports.",
        "description": "Documentation drafting and technical writing.",
        "keywords": ["write", "docs", "documentation", "readme", "changelog", "report"],
        "toolset": ["filesystem-mcp"],
        "trust_tier": "standard",
    },
    {
        "capability_id": "data",
        "name": "Data Agent",
        "role": "Queries databases and generates reports.",
        "description": "SQL queries, analysis, reporting, and chart generation.",
        "keywords": ["sql", "database", "data", "analysis", "report", "chart", "csv"],
        "toolset": ["sqlite-mcp", "filesystem-mcp", "code-sandbox-mcp"],
        "trust_tier": "standard",
    },
]


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    name: str
    role: str
    description: str
    keywords_json: str
    toolset_json: str
    trust_tier: str
    enabled: int
    created_at: str
    updated_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def seed_defaults(db_path: Path = DB_PATH) -> None:
    conn = connect(db_path)
    try:
        for capability in DEFAULT_CAPABILITIES:
            now = now_iso()
            conn.execute(
                """
                INSERT OR IGNORE INTO capability_catalog (
                    capability_id, name, role, description, keywords_json, toolset_json,
                    trust_tier, enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    capability["capability_id"],
                    capability["name"],
                    capability["role"],
                    capability["description"],
                    json.dumps(capability["keywords"], sort_keys=True),
                    json.dumps(capability["toolset"], sort_keys=True),
                    capability["trust_tier"],
                    now,
                    now,
                ),
            )
            for keyword in capability["keywords"]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO routing_rules (
                        capability_id, match_text, priority, enabled, created_at
                    ) VALUES (?, ?, ?, 1, ?)
                    """,
                    (capability["capability_id"], keyword, 100, now),
                )
        conn.commit()
    finally:
        conn.close()


def _load_capability(row: sqlite3.Row | None) -> CapabilityRecord | None:
    if row is None:
        return None
    return CapabilityRecord(
        capability_id=row["capability_id"],
        name=row["name"],
        role=row["role"],
        description=row["description"],
        keywords_json=row["keywords_json"],
        toolset_json=row["toolset_json"],
        trust_tier=row["trust_tier"],
        enabled=row["enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def register_capability(
    capability_id: str,
    name: str,
    role: str,
    description: str,
    keywords: list[str] | None = None,
    toolset: list[str] | None = None,
    trust_tier: str = "standard",
    enabled: bool = True,
    db_path: Path = DB_PATH,
) -> CapabilityRecord:
    now = now_iso()
    conn = connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO capability_catalog (
                capability_id, name, role, description, keywords_json, toolset_json,
                trust_tier, enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(capability_id) DO UPDATE SET
                name = excluded.name,
                role = excluded.role,
                description = excluded.description,
                keywords_json = excluded.keywords_json,
                toolset_json = excluded.toolset_json,
                trust_tier = excluded.trust_tier,
                enabled = excluded.enabled,
                updated_at = excluded.updated_at
            """,
            (
                capability_id,
                name,
                role,
                description,
                json.dumps(keywords or [], sort_keys=True),
                json.dumps(toolset or [], sort_keys=True),
                trust_tier,
                1 if enabled else 0,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM capability_catalog WHERE capability_id = ?", (capability_id,)).fetchone()
        return _load_capability(row)  # type: ignore[return-value]
    finally:
        conn.close()


def list_capabilities(db_path: Path = DB_PATH) -> list[CapabilityRecord]:
    conn = connect(db_path)
    try:
        seed_defaults(db_path)
        rows = conn.execute("SELECT * FROM capability_catalog ORDER BY capability_id ASC").fetchall()
        return [record for record in (_load_capability(row) for row in rows) if record is not None]
    finally:
        conn.close()


def _metric_row(conn: sqlite3.Connection, capability_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM capability_metrics WHERE capability_id = ?",
        (capability_id,),
    ).fetchone()


def _tokenize(text: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    return {token for token in cleaned.split() if token}


def _semantic_overlap_score(task_text: str, capability: sqlite3.Row) -> dict[str, Any]:
    task_tokens = _tokenize(task_text)
    capability_tokens = _tokenize(
        " ".join(
            [
                capability["name"],
                capability["role"],
                capability["description"],
                " ".join(json.loads(capability["keywords_json"])),
                " ".join(json.loads(capability["toolset_json"])),
            ]
        )
    )
    if not task_tokens or not capability_tokens:
        return {
            "semantic_score": 0.0,
            "token_overlap": [],
            "task_token_count": len(task_tokens),
            "capability_token_count": len(capability_tokens),
        }

    overlap = sorted(task_tokens & capability_tokens)
    union = task_tokens | capability_tokens
    semantic_score = len(overlap) / len(union)
    return {
        "semantic_score": semantic_score,
        "token_overlap": overlap,
        "task_token_count": len(task_tokens),
        "capability_token_count": len(capability_tokens),
    }


def _historical_score(conn: sqlite3.Connection, capability_id: str) -> dict[str, Any]:
    metrics = _metric_row(conn, capability_id)
    if metrics is None:
        return {
            "historical_score": 0.5,
            "success_rate": 0.5,
            "validation_rate": 0.5,
            "cost_per_success": 1.0,
        }

    attempts = max(int(metrics["attempt_count"]), 0)
    successes = max(int(metrics["success_count"]), 0)
    validation_passes = max(int(metrics["validation_pass_count"]), 0)
    validation_rate = validation_passes / attempts if attempts else 0.5
    success_rate = successes / attempts if attempts else 0.5
    average_token_cost = float(metrics["average_token_cost"]) if float(metrics["average_token_cost"]) > 0 else 1.0
    cost_per_success = float(metrics["total_cost"]) / successes if successes else average_token_cost
    historical_score = (success_rate + validation_rate) / 2
    return {
        "historical_score": historical_score,
        "success_rate": success_rate,
        "validation_rate": validation_rate,
        "cost_per_success": cost_per_success,
    }


def score_capability(conn: sqlite3.Connection, capability_id: str, task_text: str) -> dict[str, Any]:
    capability = conn.execute(
        "SELECT * FROM capability_catalog WHERE capability_id = ? AND enabled = 1",
        (capability_id,),
    ).fetchone()
    if capability is None:
        return {"score": 0.0, "reason": "disabled or missing"}

    keywords = json.loads(capability["keywords_json"])
    lowered_task = task_text.lower()
    keyword_hits = sum(1 for keyword in keywords if keyword.lower() in lowered_task)
    keyword_bonus = min(keyword_hits * 0.1, 0.3)

    semantic = _semantic_overlap_score(task_text, capability)
    historical = _historical_score(conn, capability_id)
    validation_score = historical["validation_rate"]
    confidence = min(
        1.0,
        (semantic["semantic_score"] * 0.5)
        + (historical["historical_score"] * 0.3)
        + (validation_score * 0.2)
        + keyword_bonus,
    )

    cost_per_success = max(historical["cost_per_success"], 1.0)
    utility = confidence * historical["success_rate"]
    utility_per_cost = utility / cost_per_success

    return {
        "score": utility_per_cost,
        "confidence": confidence,
        "success_rate": historical["success_rate"],
        "validation_rate": validation_score,
        "cost_per_success": cost_per_success,
        "keyword_hits": keyword_hits,
        "semantic_score": semantic["semantic_score"],
        "token_overlap": semantic["token_overlap"],
        "historical_score": historical["historical_score"],
    }


def route_task(task_text: str, db_path: Path = DB_PATH) -> dict[str, Any]:
    conn = connect(db_path)
    try:
        seed_defaults(db_path)
        candidates = []
        for capability in conn.execute("SELECT * FROM capability_catalog WHERE enabled = 1").fetchall():
            rule = conn.execute(
                """
                SELECT match_text FROM routing_rules
                WHERE capability_id = ? AND enabled = 1
                ORDER BY priority ASC, rule_id ASC
                """,
                (capability["capability_id"],),
            ).fetchone()
            score = score_capability(conn, capability["capability_id"], task_text)
            candidates.append(
                {
                    "capability_id": capability["capability_id"],
                    "name": capability["name"],
                    "score": score["score"],
                    "confidence": score["confidence"],
                    "semantic_score": score["semantic_score"],
                    "historical_score": score["historical_score"],
                    "validation_rate": score["validation_rate"],
                    "selected_rule": rule["match_text"] if rule else None,
                    "details": score,
                }
            )

        if not candidates:
            raise ValueError("No enabled capabilities available")

        selected = max(candidates, key=lambda candidate: candidate["score"])
        conn.execute(
            """
            INSERT INTO routing_decisions (
                timestamp, task_text, selected_capability_id, selected_rule, decision_factors_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                now_iso(),
                task_text,
                selected["capability_id"],
                selected["selected_rule"],
                json.dumps({"candidates": candidates, "selected": selected}, sort_keys=True),
            ),
        )
        conn.commit()
        return {
            "task_text": task_text,
            "selected_capability_id": selected["capability_id"],
            "selected_name": selected["name"],
            "score": selected["score"],
            "confidence": selected["confidence"],
            "semantic_score": selected["semantic_score"],
            "historical_score": selected["historical_score"],
            "validation_rate": selected["validation_rate"],
            "selected_rule": selected["selected_rule"],
            "candidates": candidates,
        }
    finally:
        conn.close()


def print_capability(record: CapabilityRecord) -> None:
    keywords = ", ".join(json.loads(record.keywords_json))
    print(f"{record.capability_id:<12} {record.name:<18} {record.trust_tier:<10} enabled={record.enabled} keywords=[{keywords}]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS capability registry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register", help="Register or update a capability")
    register_parser.add_argument("capability_id")
    register_parser.add_argument("--name", required=True)
    register_parser.add_argument("--role", required=True)
    register_parser.add_argument("--description", required=True)
    register_parser.add_argument("--keywords", nargs="*", default=[])
    register_parser.add_argument("--toolset", nargs="*", default=[])
    register_parser.add_argument("--trust-tier", default="standard")
    register_parser.add_argument("--disabled", action="store_true")

    subparsers.add_parser("list", help="List registered capabilities")

    route_parser = subparsers.add_parser("route", help="Select a capability for a task")
    route_parser.add_argument("task_text")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "register":
        record = register_capability(
            capability_id=args.capability_id,
            name=args.name,
            role=args.role,
            description=args.description,
            keywords=args.keywords,
            toolset=args.toolset,
            trust_tier=args.trust_tier,
            enabled=not args.disabled,
        )
        print_capability(record)
        return 0

    if args.command == "list":
        capabilities = list_capabilities()
        if not capabilities:
            print("No capabilities registered.")
            return 0
        print(f"{'Capability':<12} {'Name':<18} {'Trust':<10} Status Keywords")
        print("-" * 100)
        for capability in capabilities:
            print_capability(capability)
        return 0

    if args.command == "route":
        result = route_task(args.task_text)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())