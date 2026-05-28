from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import governance
import langgraph_pipeline


TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = "jarvis-orchestration"

# Temporal is the PRIMARY durable execution path.
# Falls back to local durable_workflow.py when Temporal is unreachable.


@dataclass
class PipelineInput:
    task_text: str
    agent_id: str
    db_path: str
    approvals_json: str
    vault_path: str | None


@dataclass
class PipelineOutput:
    result_json: str


# ---------------------------------------------------------------------------
# Temporal activities and workflows
# ---------------------------------------------------------------------------

try:
    from temporalio import activity, workflow
    from temporalio.client import Client
    from temporalio.worker import Worker

    @activity.defn
    async def run_langgraph_pipeline(input: PipelineInput) -> str:
        approvals = json.loads(input.approvals_json) if input.approvals_json else {}
        db_path = Path(input.db_path)
        vault_path = Path(input.vault_path) if input.vault_path else None

        result = langgraph_pipeline.run_pipeline(
            task_text=input.task_text,
            agent_id=input.agent_id,
            db_path=db_path,
            vault_path=vault_path,
            approvals=approvals,
        )
        return json.dumps(result, sort_keys=True)

    @workflow.defn
    class LangGraphOrchestrationWorkflow:
        @workflow.run
        async def run(self, input: PipelineInput) -> str:
            result = await workflow.execute_activity(
                run_langgraph_pipeline,
                input,
                start_to_close_timeout=timedelta(seconds=300),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=30),
                ),
            )
            return result

    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    LangGraphOrchestrationWorkflow = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Temporal client helpers
# ---------------------------------------------------------------------------

async def _run_pipeline_via_temporal(
    task_text: str,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
    vault_path: Path | None = None,
    approvals: dict[str, int] | None = None,
) -> dict[str, Any]:
    if not TEMPORAL_AVAILABLE:
        raise ConnectionError("temporalio package not installed")

    client = await Client.connect(TEMPORAL_HOST)

    input_data = PipelineInput(
        task_text=task_text,
        agent_id=agent_id,
        db_path=str(db_path),
        approvals_json=json.dumps(approvals or {}),
        vault_path=str(vault_path) if vault_path else None,
    )

    result = await client.execute_workflow(
        LangGraphOrchestrationWorkflow.run,
        input_data,
        id=f"jarvis-{hash(task_text) & 0xFFFFFFFF:08x}",
        task_queue=TASK_QUEUE,
        id_reuse_policy=workflow.WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
    return json.loads(result)


def _is_temporal_reachable() -> bool:
    """Quick TCP check to see if Temporal is up."""
    import socket
    host, port_str = TEMPORAL_HOST.split(":", 1)
    port = int(port_str)
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, TimeoutError):
        return False


# ---------------------------------------------------------------------------
# Primary API: run_pipeline_durable
# ---------------------------------------------------------------------------

def run_pipeline_durable(
    task_text: str,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
    vault_path: Path | None = None,
    approvals: dict[str, int] | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Run the LangGraph pipeline with durable execution.

    Priority:
      1. Temporal.io (if available and reachable)
      2. Local durable_workflow.py (SQLite-backed retry logic)
    """
    # --- Priority 1: Temporal ---
    if TEMPORAL_AVAILABLE and _is_temporal_reachable():
        try:
            result = asyncio.run(
                _run_pipeline_via_temporal(
                    task_text=task_text,
                    agent_id=agent_id,
                    db_path=db_path,
                    vault_path=vault_path,
                    approvals=approvals,
                )
            )
            result["execution_backend"] = "temporal"
            return result
        except Exception:
            pass  # Fall through to local

    # --- Priority 2: Local durable_workflow ---
    import durable_workflow

    input_data = {
        "task_text": task_text,
        "agent_id": agent_id,
        "db_path": str(db_path),
        "approvals": approvals or {},
    }
    if vault_path:
        input_data["vault_path"] = str(vault_path)

    run = durable_workflow.execute_workflow(
        workflow_type="orchestration_graph",
        input_data=input_data,
        steps=[],
        max_retries=max_retries,
        db_path=Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "graph.db",
    )

    # Run the actual pipeline
    pipeline_result = langgraph_pipeline.run_pipeline(
        task_text=task_text,
        agent_id=agent_id,
        db_path=db_path,
        vault_path=vault_path,
        approvals=approvals,
    )

    return {
        "task_text": task_text,
        "graph": pipeline_result.get("graph", "langgraph-v1"),
        "run_id": run.run_id,
        "nodes": pipeline_result.get("nodes", []),
        "final_state": pipeline_result.get("final_state", "ok"),
        "retry_count": run.retry_count,
        "error": run.error or pipeline_result.get("error", ""),
        "execution_backend": "local-durable",
    }


# ---------------------------------------------------------------------------
# Legacy API (backwards compatible)
# ---------------------------------------------------------------------------

def run_pipeline_via_temporal(
    task_text: str,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
    vault_path: Path | None = None,
    approvals: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Legacy wrapper — calls run_pipeline_durable internally."""
    return run_pipeline_durable(
        task_text=task_text,
        agent_id=agent_id,
        db_path=db_path,
        vault_path=vault_path,
        approvals=approvals,
    )


# ---------------------------------------------------------------------------
# Temporal worker
# ---------------------------------------------------------------------------

async def _start_worker() -> None:
    if not TEMPORAL_AVAILABLE:
        raise RuntimeError("temporalio package not installed — cannot start worker")
    client = await Client.connect(TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[LangGraphOrchestrationWorkflow],
        activities=[run_langgraph_pipeline],
    )
    await worker.run()


def start_worker() -> None:
    asyncio.run(_start_worker())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        print("Starting Temporal worker for JARVIS orchestration...")
        start_worker()
    else:
        result = run_pipeline_durable("Test Temporal integration", agent_id="temporal-test")
        print(json.dumps(result, indent=2, sort_keys=True))
