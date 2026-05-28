#!/usr/bin/env python3
"""Task commander for JARVIS.

Takes a task, routes it to the best capability, and opens an approval request
for the runtime creation step so the operator can authorize execution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import capability_registry
import governance


def plan_task(task_text: str, agent_id: str = "orchestrator", db_path: Path = governance.DB_PATH) -> dict[str, object]:
    routing = capability_registry.route_task(task_text, db_path=db_path)
    approval_id = governance.enqueue_approval(
        agent_id=agent_id,
        action_type="create_runtime",
        action_detail=f"Create runtime for {routing['selected_capability_id']}: {task_text}",
        risk_level="high",
        db_path=db_path,
    )
    return {
        "task_text": task_text,
        "approval_id": approval_id,
        "selected_capability_id": routing["selected_capability_id"],
        "selected_name": routing["selected_name"],
        "score": routing["score"],
        "confidence": routing["confidence"],
        "selected_rule": routing["selected_rule"],
        "candidates": routing["candidates"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS commander")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Route a task and request approval")
    plan_parser.add_argument("task_text")
    plan_parser.add_argument("--agent-id", default="orchestrator")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "plan":
        result = plan_task(args.task_text, agent_id=args.agent_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())