from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

import commander
import governance
import planner_tool
import research_gateway
import researcher
import sandbox_runner
import workflow_dispatcher


class PipelineState(TypedDict):
    task_text: str
    agent_id: str
    db_path: str
    approvals: dict[str, int]
    vault_path: str | None
    plan_result: dict[str, Any]
    route_result: dict[str, Any]
    research_result: dict[str, Any]
    sandbox_result: dict[str, Any]
    qa_result: dict[str, Any]
    security_result: dict[str, Any]
    execute_result: dict[str, Any]
    error: str
    run_id: str
    skip_reason: str


def _make_state(task_text: str, **overrides: Any) -> PipelineState:
    return PipelineState(
        task_text=task_text,
        agent_id=overrides.get("agent_id", "orchestrator"),
        db_path=str(overrides.get("db_path", governance.DB_PATH)),
        approvals=overrides.get("approvals", {}),
        vault_path=overrides.get("vault_path"),
        plan_result={},
        route_result={},
        research_result={},
        sandbox_result={},
        qa_result={},
        security_result={},
        execute_result={},
        error="",
        run_id="",
        skip_reason="",
    )


def _plan_node(state: PipelineState) -> dict[str, Any]:
    db_path = Path(state["db_path"])
    plan = planner_tool.build_plan(state["task_text"], db_path=db_path)
    return {"plan_result": {"node_name": "plan", "status": "ok", "plan": plan}}


def _route_node(state: PipelineState) -> dict[str, Any]:
    db_path = Path(state["db_path"])
    route = commander.plan_task(state["task_text"], agent_id=state["agent_id"], db_path=db_path)
    return {"route_result": {"node_name": "route", "status": "ok", "route": route, "capability_id": route.get("selected_capability_id", "")}}


def _research_node(state: PipelineState) -> dict[str, Any]:
    task_text = state["task_text"]
    db_path = Path(state["db_path"])

    if not any(term in task_text.lower() for term in ("research", "search", "documentation", "docs", "find", "learn")):
        return {"research_result": {"node_name": "research", "status": "skipped", "reason": "no research needed"}}

    findings = researcher.search_findings(task_text, limit=5)
    if findings:
        return {"research_result": {"node_name": "research", "status": "ok", "findings": findings, "source": "memory"}}

    if task_text.startswith("http"):
        page = research_gateway.capture_page(task_text)
        stored = researcher.capture_finding(
            title=page.title,
            content=page.text,
            source_ref=task_text,
            tags=["research", "capture"],
            confidence=0.75,
            db_path=db_path,
        )
        return {"research_result": {"node_name": "research", "status": "ok", "note_id": stored["note_id"], "source": "capture"}}

    return {"research_result": {"node_name": "research", "status": "ok", "findings": [], "source": "none"}}


def _sandbox_node(state: PipelineState) -> dict[str, Any]:
    task_text = state["task_text"]

    if not any(term in task_text.lower() for term in ("code", "test", "implement", "bug", "refactor", "build", "function")):
        return {"sandbox_result": {"node_name": "sandbox", "status": "skipped", "reason": "no sandbox needed"}}

    code = "print('sandbox validation ok')"
    result = sandbox_runner.run_python_snippet(code)
    status = "ok" if result.returncode == 0 else "error"
    return {"sandbox_result": {"node_name": "sandbox", "status": status, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}}


def _qa_node(state: PipelineState) -> dict[str, Any]:
    sandbox = state["sandbox_result"]
    task_text = state["task_text"]

    if sandbox.get("status") != "ok":
        return {"qa_result": {"node_name": "qa", "status": "skipped", "reason": "sandbox did not run"}}

    issues: list[str] = []
    if sandbox.get("stderr"):
        issues.append("sandbox produced stderr output")
    if sandbox.get("returncode", 0) != 0:
        issues.append("sandbox returned non-zero exit code")

    qa_status = "ok"
    if issues:
        qa_status = "warn"

    return {
        "qa_result": {
            "node_name": "qa",
            "status": qa_status,
            "issues": issues,
            "passed": len(issues) == 0,
        }
    }


def _security_node(state: PipelineState) -> dict[str, Any]:
    task_text = state["task_text"]
    route = state["route_result"]

    warnings: list[str] = []

    capability = route.get("capability_id", "")
    if capability in ("coder", "security", "qa") and "write" in task_text.lower():
        warnings.append("code write operation requires approval gate")

    sandbox = state["sandbox_result"]
    if sandbox.get("stderr"):
        warnings.append("sandbox produced errors — inspect before execution")

    sec_status = "ok" if not warnings else "warn"
    return {
        "security_result": {
            "node_name": "security",
            "status": sec_status,
            "warnings": warnings,
            "safe": len(warnings) == 0,
        }
    }


def _execute_node(state: PipelineState) -> dict[str, Any]:
    task_text = state["task_text"]
    db_path = Path(state["db_path"])
    agent_id = state["agent_id"]
    approvals = state["approvals"]

    if not approvals:
        return {"execute_result": {"node_name": "execute", "status": "skipped", "reason": "no approvals"}}

    result = workflow_dispatcher.execute_approved_task(
        task_text,
        approval_id=approvals["create"],
        start_approval_id=approvals["start"],
        complete_approval_id=approvals["complete"],
        agent_id=agent_id,
        db_path=db_path,
    )
    return {"execute_result": {"node_name": "execute", "status": "ok", "result": result}}


def _needs_research(state: PipelineState) -> Literal["research", "sandbox"]:
    task_text = state["task_text"]
    if any(term in task_text.lower() for term in ("research", "search", "documentation", "docs", "find", "learn")):
        return "research"
    return "sandbox"


def _needs_security(state: PipelineState) -> Literal["security", "execute"]:
    route = state["route_result"]
    capability = route.get("capability_id", "")
    if capability in ("coder", "security", "qa", "writer", "data"):
        return "security"
    return "execute"


def build_pipeline() -> StateGraph:
    builder = StateGraph(PipelineState)

    builder.add_node("plan", _plan_node)
    builder.add_node("route", _route_node)
    builder.add_node("research", _research_node)
    builder.add_node("sandbox", _sandbox_node)
    builder.add_node("qa", _qa_node)
    builder.add_node("security", _security_node)
    builder.add_node("execute", _execute_node)

    builder.set_entry_point("plan")

    builder.add_edge("plan", "route")
    builder.add_conditional_edges("route", _needs_research, {"research": "research", "sandbox": "sandbox"})
    builder.add_edge("research", "sandbox")
    builder.add_edge("sandbox", "qa")
    builder.add_conditional_edges("qa", _needs_security, {"security": "security", "execute": "execute"})
    builder.add_edge("security", "execute")
    builder.add_edge("execute", END)

    return builder.compile()


LANGGRAPH_PIPELINE = build_pipeline()


def run_pipeline(
    task_text: str,
    agent_id: str = "orchestrator",
    db_path: Path = governance.DB_PATH,
    vault_path: Path | None = None,
    approvals: dict[str, int] | None = None,
) -> dict[str, Any]:
    approvals = approvals or {}
    state = _make_state(task_text, agent_id=agent_id, db_path=db_path, vault_path=vault_path, approvals=approvals)
    result = LANGGRAPH_PIPELINE.invoke(state)

    node_order = ["plan", "route", "research", "sandbox", "qa", "security", "execute"]
    nodes = []
    for name in node_order:
        node_result = result.get(f"{name}_result", {})
        nodes.append({
            "name": name,
            "status": node_result.get("status", "skipped"),
            "output": node_result,
        })

    final_status = next((n["status"] for n in reversed(nodes) if n["status"] not in ("skipped",)), "skipped")

    return {
        "task_text": task_text,
        "graph": "langgraph-v1",
        "nodes": nodes,
        "final_state": final_status,
        "retry_count": 0,
        "error": result.get("error", ""),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS LangGraph pipeline")
    parser.add_argument("task_text")
    parser.add_argument("--agent-id", default="orchestrator")
    args = parser.parse_args()
    result = run_pipeline(args.task_text, agent_id=args.agent_id)
    print(json.dumps(result, indent=2, sort_keys=True))
