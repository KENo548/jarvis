#!/usr/bin/env python3
"""Structured planning helper for JARVIS.

This turns the Phase 2 memory layer into a usable planning surface: it reads
relevant stored notes, generates a simple deterministic execution plan, and
persists the result for later reuse.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import memory_store


def build_plan(
    objective: str,
    db_path: Path | None = None,
    vault_path: Path | None = None,
) -> dict[str, object]:
    context_notes = memory_store.search_notes(objective, db_path=db_path or memory_store.DB_PATH)
    tokens = [token for token in objective.lower().split() if token]

    if any(term in objective.lower() for term in ("memory", "research", "search")):
        steps = [
            "Review existing research notes",
            "Collect additional supporting findings",
            "Store concise summary in the memory vault",
        ]
        risk = "medium"
    elif any(term in objective.lower() for term in ("code", "bug", "test", "implement")):
        steps = [
            "Inspect the target code path",
            "Draft or update tests",
            "Apply the smallest safe change",
            "Validate the result",
        ]
        risk = "high"
    else:
        steps = [
            "Clarify the objective",
            "Identify dependencies",
            "Execute the smallest useful next action",
        ]
        risk = "medium"

    plan = {
        "objective": objective,
        "risk_level": risk,
        "estimated_steps": len(steps),
        "key_terms": tokens[:8],
        "context_notes": [
            {
                "note_id": note.note_id,
                "title": note.title,
                "source_ref": note.source_ref,
                "confidence": note.confidence,
            }
            for note in context_notes
        ],
        "steps": steps,
    }

    plan_note = memory_store.store_note(
        title=f"Plan: {objective}",
        content=json.dumps(plan, indent=2, sort_keys=True),
        source_type="plan",
        source_ref=f"planner:{objective}",
        tags=["plan", "phase2"],
        confidence=0.75,
        db_path=db_path or memory_store.DB_PATH,
    )
    memory_store.export_to_obsidian(plan_note, vault_path=vault_path or memory_store.OBSIDIAN_VAULT)
    plan["note_id"] = plan_note.note_id
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS planner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Build a structured plan from an objective")
    plan_parser.add_argument("objective")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "plan":
        result = build_plan(args.objective)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())