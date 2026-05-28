#!/usr/bin/env python3
"""Approved task workflow dispatcher for JARVIS.

This is the first concrete agent-workflow layer: it takes a routed task,
requests or consumes approvals, creates a runtime, starts it, and completes it
while preserving the audit trail and kill-switch enforcement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import commander
import governance
import runtime_lifecycle


def dispatch_task(
    task_text: str,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
) -> dict[str, object]:
    plan = commander.plan_task(task_text, agent_id=agent_id, db_path=db_path)
    return {
        "task_text": task_text,
        "plan": plan,
        "workflow_state": "AWAITING_APPROVAL",
    }


def execute_approved_task(
    task_text: str,
    approval_id: int,
    start_approval_id: int,
    complete_approval_id: int,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
) -> dict[str, object]:
    plan = commander.plan_task(task_text, agent_id=agent_id, db_path=db_path)
    if not governance.is_approved(approval_id, db_path=db_path):
        raise PermissionError(f"Runtime creation approval {approval_id} is not approved")
    runtime = runtime_lifecycle.create_runtime(
        task_id=f"task-{approval_id}",
        capability_id=str(plan["selected_capability_id"]),
        agent_id=agent_id,
        requested_action=task_text,
        approval_id=approval_id,
        db_path=db_path,
    )
    started = runtime_lifecycle.start_runtime_with_approval(runtime.runtime_id, start_approval_id, db_path=db_path)
    completed = runtime_lifecycle.complete_runtime_with_approval(
        runtime.runtime_id,
        reason="workflow completed",
        approval_id=complete_approval_id,
        db_path=db_path,
    )
    return {
        "task_text": task_text,
        "plan": plan,
        "runtime_id": runtime.runtime_id,
        "state": completed.state,
        "started_state": started.state,
        "approval_ids": {
            "create": approval_id,
            "start": start_approval_id,
            "complete": complete_approval_id,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS workflow dispatcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dispatch_parser = subparsers.add_parser("dispatch", help="Route a task and queue workflow approval")
    dispatch_parser.add_argument("task_text")
    dispatch_parser.add_argument("--agent-id", default="orchestrator")

    execute_parser = subparsers.add_parser("execute", help="Execute an already approved workflow")
    execute_parser.add_argument("task_text")
    execute_parser.add_argument("--approval-id", type=int, required=True)
    execute_parser.add_argument("--start-approval-id", type=int, required=True)
    execute_parser.add_argument("--complete-approval-id", type=int, required=True)
    execute_parser.add_argument("--agent-id", default="orchestrator")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "dispatch":
        result = dispatch_task(args.task_text, agent_id=args.agent_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "execute":
        result = execute_approved_task(
            args.task_text,
            approval_id=args.approval_id,
            start_approval_id=args.start_approval_id,
            complete_approval_id=args.complete_approval_id,
            agent_id=args.agent_id,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())