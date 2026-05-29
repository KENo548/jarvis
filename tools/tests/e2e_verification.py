#!/usr/bin/env python3
"""SAGE Phase 0+1 E2E Verification Test Suite.

Runs 10 canonical tasks through the SAGE agents, validates the observability
layer, and produces a verification report.  Exit code 0 = PASS (7/10+),
exit code 1 = FAIL.
"""

import json
import sqlite3
import sys
import time
import traceback
import uuid
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
TOOLS_DIR = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, TOOLS_DIR)

from llm_client import llm_call
from agents.commander import route_task
from agents.planner import create_plan
from agents.engineer import generate_code
from agents.researcher import research_topic
from agents.memory_coordinator import coordinate_memory
from agents.tool_operator import plan_tool_usage
from observability.interaction_logger import init_db, log_interaction, get_interaction, get_stats
from observability.auto_eval import evaluate

RESULTS_DIR = Path(r"C:\jarvis\memory\test_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PASS_THRESHOLD = 7  # out of 10


# ---------------------------------------------------------------------------
# Canonical test definitions
# ---------------------------------------------------------------------------

def _validate_commander_research(result):
    agent = result.get("selected_agent", "").lower()
    conf = result.get("confidence", 0)
    if agent == "researcher" and conf > 0.7:
        return True, f"routed to researcher (conf={conf:.2f})"
    return False, f"expected researcher with conf>0.7, got agent={agent!r} conf={conf}"


def _validate_commander_engineer(result):
    agent = result.get("selected_agent", "").lower()
    conf = result.get("confidence", 0)
    if agent == "engineer" and conf > 0.7:
        return True, f"routed to engineer (conf={conf:.2f})"
    return False, f"expected engineer with conf>0.7, got agent={agent!r} conf={conf}"


def _validate_commander_memory(result):
    agent = result.get("selected_agent", "").lower()
    conf = result.get("confidence", 0)
    if agent == "memory_coordinator" and conf > 0.7:
        return True, f"routed to memory_coordinator (conf={conf:.2f})"
    return False, f"expected memory_coordinator with conf>0.7, got agent={agent!r} conf={conf}"


def _validate_planner(result):
    steps = result.get("steps", [])
    n = len(steps)
    if 3 <= n <= 8:
        # Verify each step has required fields
        for s in steps:
            if "description" not in s:
                return False, f"step missing 'description': {s}"
        return True, f"produced {n} valid steps"
    return False, f"expected 3-8 steps, got {n} (keys: {list(result.keys())})"


def _validate_engineer(result):
    code = result.get("code", "")
    if not code:
        return False, "no 'code' field in response"
    if "def " in code or "class " in code:
        return True, f"generated code ({len(code)} chars) with def/class"
    return False, "code does not contain 'def' or 'class'"


def _validate_researcher(result):
    summary = result.get("summary", "")
    findings = result.get("key_findings", [])
    if summary and len(findings) >= 1:
        return True, f"summary ({len(summary)} chars) + {len(findings)} findings"
    return False, f"missing summary ({len(summary)} chars) or findings ({len(findings)})"


def _validate_memory_coordinator(result):
    updates = result.get("memory_updates", {})
    if isinstance(updates, dict) and len(updates) > 0:
        return True, f"produced memory_updates for {len(updates)} category(ies)"
    return False, f"expected non-empty memory_updates dict, got {type(updates)}: {updates}"


def _validate_tool_operator(result):
    calls = result.get("tool_calls", [])
    if isinstance(calls, list) and len(calls) >= 1:
        for c in calls:
            if "tool" not in c:
                return False, f"tool_call missing 'tool' field: {c}"
        return True, f"produced {len(calls)} tool_call(s)"
    return False, f"expected tool_calls array with >=1 entry, got {calls}"


def _validate_llm_client(result):
    # result is the LLMResponse object
    text = getattr(result, "text", "") or ""
    if "paris" in text.lower():
        tokens = getattr(result, "token_usage", {})
        total = tokens.get("total", 0) if isinstance(tokens, dict) else 0
        return True, f"LLM responded with 'Paris' ({total} tokens)"
    return False, f"expected 'Paris' in response, got: {text[:120]}..."


def _validate_observability_roundtrip(result):
    iid = result.get("interaction_id")
    if not iid:
        return False, "no interaction_id returned from log_interaction"
    row = result.get("retrieved")
    if not row:
        return False, "retrieved row is None"
    # Verify all critical fields
    required = ["interaction_id", "agent_name", "input_text", "output_text", "latency_ms", "timestamp"]
    missing = [f for f in required if f not in row]
    if missing:
        return False, f"missing fields in retrieved row: {missing}"
    if row["interaction_id"] != iid:
        return False, f"interaction_id mismatch: {row['interaction_id']} != {iid}"
    return True, f"roundtrip OK ({len(required)} fields verified)"


TESTS = [
    {
        "name": "Commander: research routing",
        "task": "Research Python security vulnerabilities",
        "agent": "commander",
        "run": lambda: route_task("Research Python security vulnerabilities"),
        "validate": _validate_commander_research,
    },
    {
        "name": "Commander: engineer routing",
        "task": "Write a sorting algorithm",
        "agent": "commander",
        "run": lambda: route_task("Write a sorting algorithm"),
        "validate": _validate_commander_engineer,
    },
    {
        "name": "Commander: memory routing",
        "task": "Remember my preference for dark mode",
        "agent": "commander",
        "run": lambda: route_task("Remember my preference for dark mode"),
        "validate": _validate_commander_memory,
    },
    {
        "name": "Planner: web scraper plan",
        "task": "Build a web scraper for product prices",
        "agent": "planner",
        "run": lambda: create_plan("Build a web scraper for product prices"),
        "validate": _validate_planner,
    },
    {
        "name": "Engineer: factorial code",
        "task": "Write a Python function to calculate factorial",
        "agent": "engineer",
        "run": lambda: generate_code("Write a Python function to calculate factorial"),
        "validate": _validate_engineer,
    },
    {
        "name": "Researcher: list comprehensions",
        "task": "What are Python list comprehensions",
        "agent": "researcher",
        "run": lambda: research_topic("What are Python list comprehensions"),
        "validate": _validate_researcher,
    },
    {
        "name": "Memory Coordinator: user preferences",
        "task": "User prefers VS Code and works on JARVIS project",
        "agent": "memory_coordinator",
        "run": lambda: coordinate_memory("User prefers VS Code and works on JARVIS project"),
        "validate": _validate_memory_coordinator,
    },
    {
        "name": "Tool Operator: file download",
        "task": "Download a file and save to desktop",
        "agent": "tool_operator",
        "run": lambda: plan_tool_usage("Download a file and save to desktop"),
        "validate": _validate_tool_operator,
    },
    {
        "name": "LLM Client: factual question",
        "task": "What is the capital of France?",
        "agent": "llm_client",
        "run": lambda: llm_call("What is the capital of France?", temperature=0.0, max_tokens=50),
        "validate": _validate_llm_client,
    },
    {
        "name": "Observability: log + retrieve roundtrip",
        "task": "Log interaction and verify retrieval",
        "agent": "observability",
        "run": lambda: _run_observability_roundtrip(),
        "validate": _validate_observability_roundtrip,
    },
]


# ---------------------------------------------------------------------------
# Observability roundtrip helper
# ---------------------------------------------------------------------------

def _run_observability_roundtrip():
    session_id = f"e2e_{uuid.uuid4().hex[:8]}"
    iid = log_interaction(
        agent_name="e2e_test_agent",
        input_text="Test input for observability roundtrip verification",
        output_text="Test output with [EMAIL REDACTED] for PII redaction check",
        model="test-model/1.0",
        duration_ms=42,
        session_id=session_id,
        reasoning_trace="test reasoning",
        domain="e2e_verification",
        token_cost_usd=0.0,
    )
    row = get_interaction(iid)
    return {"interaction_id": iid, "retrieved": row}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def _run_single(test):
    """Execute one test and return a result dict with timing and outcome."""
    t0 = time.time()
    try:
        raw_result = test["run"]()
        passed, reason = test["validate"](raw_result)
        error_msg = ""
    except Exception as exc:
        raw_result = {"error": str(exc)}
        passed = False
        reason = f"Exception: {exc}"
        error_msg = traceback.format_exc()

    latency_ms = int((time.time() - t0) * 1000)

    # Extract token/cost info from LLMResponse if present
    tokens = 0
    cost = 0.0
    if hasattr(raw_result, "token_usage"):
        tokens = getattr(raw_result, "token_usage", {}).get("total", 0)
    if hasattr(raw_result, "cost_usd"):
        cost = getattr(raw_result, "cost_usd", 0.0)

    return {
        "name": test["name"],
        "task": test["task"],
        "agent": test["agent"],
        "passed": passed,
        "reason": reason,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "cost_usd": cost,
        "error": error_msg,
        "result_preview": _preview(raw_result),
    }


def _preview(result, max_len=200):
    """Truncated string representation of a result."""
    try:
        if hasattr(result, "text"):
            s = result.text
        elif isinstance(result, dict):
            s = json.dumps(result, default=str)
        else:
            s = str(result)
    except Exception:
        s = str(result)
    return s[:max_len] + ("..." if len(s) > max_len else "")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _print_table(results):
    """Print a formatted results table to stdout."""
    header = f"{'#':<3} {'Task':<42} {'Status':<7} {'Latency':>8} {'Tokens':>7} {'Cost':>10}  Reason"
    print(header)
    print("-" * len(header))
    for i, r in enumerate(results, 1):
        status = "PASS" if r["passed"] else "FAIL"
        print(
            f"{i:<3} {r['name']:<42} {status:<7} {r['latency_ms']:>6}ms"
            f" {r['tokens']:>7} ${r['cost_usd']:.6f}  {r['reason']}"
        )


def _print_summary(results):
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    total_cost = sum(r["cost_usd"] for r in results)
    avg_latency = (
        sum(r["latency_ms"] for r in results) // total if total else 0
    )
    overall = "PASS" if passed >= PASS_THRESHOLD else "FAIL"
    print()
    print(f"  Result:    {passed}/{total} passed (threshold {PASS_THRESHOLD}/10) -> {overall}")
    print(f"  Total cost:    ${total_cost:.6f}")
    print(f"  Avg latency:   {avg_latency}ms")
    print()
    return overall, passed, total, total_cost, avg_latency


def _save_report(results, overall, passed, total, total_cost, avg_latency):
    """Persist results as JSON with timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "run_id": f"e2e_{ts}",
        "timestamp": ts,
        "overall": overall,
        "passed": passed,
        "total": total,
        "pass_threshold": PASS_THRESHOLD,
        "total_cost_usd": round(total_cost, 6),
        "avg_latency_ms": avg_latency,
        "tests": results,
    }
    out_path = RESULTS_DIR / f"e2e_verification_{ts}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"  Report saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_all():
    """Run the full E2E verification suite."""
    print("=" * 80)
    print("  SAGE Phase 0+1 - E2E Verification Suite")
    print("=" * 80)
    print()

    # Ensure DB exists
    init_db()
    print("  Database initialized.\n")

    results = []
    for test in TESTS:
        print(f"  Running: {test['name']} ... ", end="", flush=True)
        r = _run_single(test)
        tag = "OK" if r["passed"] else "FAIL"
        print(f"{tag} ({r['latency_ms']}ms)")
        results.append(r)

    print()
    _print_table(results)
    overall, passed, total, total_cost, avg_latency = _print_summary(results)
    report_path = _save_report(results, overall, passed, total, total_cost, avg_latency)

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run_all())
