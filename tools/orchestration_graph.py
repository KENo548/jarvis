from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import governance
import temporal_integration


GRAPH_DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "graph.db"


@dataclass(frozen=True)
class GraphNodeResult:
    name: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)


def run_graph(
    task_text: str,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
    vault_path: Path | None = None,
    approvals: dict[str, int] | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Run the orchestration graph with durable execution.

    Delegates to temporal_integration.run_pipeline_durable which tries
    Temporal.io first, then falls back to local SQLite-backed durable workflow.
    """
    result = temporal_integration.run_pipeline_durable(
        task_text=task_text,
        agent_id=agent_id,
        db_path=db_path,
        vault_path=vault_path,
        approvals=approvals,
        max_retries=max_retries,
    )
    return result


def get_graph_run(run_id: str) -> dict[str, Any] | None:
    import durable_workflow
    run = durable_workflow.get_run(run_id, db_path=GRAPH_DB_PATH)
    if run is None:
        return None

    input_data = json.loads(run.input_json) if run.input_json else {}

    return {
        "run_id": run.run_id,
        "workflow_type": run.workflow_type,
        "state": run.state,
        "error": run.error,
        "retry_count": run.retry_count,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
    }


def retry_graph_run(run_id: str) -> dict[str, Any] | None:
    import durable_workflow
    run = durable_workflow.retry_failed_run(run_id, db_path=GRAPH_DB_PATH)
    if run is None:
        return None

    input_data = json.loads(run.input_json) if run.input_json else {}
    task_text = input_data.get("task_text", "")
    agent_id = input_data.get("agent_id", "orchestrator")

    return run_graph(
        task_text=task_text,
        agent_id=agent_id,
        db_path=Path(input_data.get("db_path", str(governance.DB_PATH))),
        approvals=input_data.get("approvals", {}),
        max_retries=run.max_retries,
    )


def list_graph_runs(limit: int = 20) -> list[dict[str, Any]]:
    import durable_workflow
    runs = durable_workflow.list_runs(limit=limit, db_path=GRAPH_DB_PATH)
    return [
        {
            "run_id": r.run_id,
            "state": r.state,
            "workflow_type": r.workflow_type,
            "created_at": r.created_at,
            "completed_at": r.completed_at,
            "retry_count": r.retry_count,
            "error": r.error,
        }
        for r in runs
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS orchestration graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the orchestration graph for a task")
    run_parser.add_argument("task_text")
    run_parser.add_argument("--agent-id", default="orchestrator")

    get_parser = subparsers.add_parser("get", help="Get a graph run by ID")
    get_parser.add_argument("run_id")

    retry_parser = subparsers.add_parser("retry", help="Retry a failed graph run")
    retry_parser.add_argument("run_id")

    list_parser = subparsers.add_parser("list", help="List graph runs")
    list_parser.add_argument("--limit", type=int, default=20)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "run":
        result = run_graph(args.task_text, agent_id=args.agent_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "get":
        result = get_graph_run(args.run_id)
        if result is None:
            print(f"Run {args.run_id} not found")
            return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "retry":
        result = retry_graph_run(args.run_id)
        if result is None:
            print(f"Run {args.run_id} not found or not failed")
            return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "list":
        runs = list_graph_runs(limit=args.limit)
        print(json.dumps(runs, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
