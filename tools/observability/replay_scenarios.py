"""Benchmark replay scenarios for regression testing the SAGE AI ecosystem."""

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from llm_client import chat_completion
except ImportError:
    chat_completion = None  # type: ignore[assignment]

SCENARIOS: list[dict[str, Any]] = [
    {
        "scenario_id": "replay_001",
        "name": "Simple web search",
        "description": "User asks to search the web for information about a topic.",
        "input_text": "Search the web for the latest news about quantum computing.",
        "expected_behavior": "The agent should route to the researcher agent and perform a web search.",
        "agent_expected": "researcher",
        "tool_expected": ["web_search", "browse"],
        "pass_criteria": {
            "agent_selected": "researcher",
            "tool_called": True,
            "output_not_empty": True,
        },
    },
    {
        "scenario_id": "replay_002",
        "name": "Write a Python function",
        "description": "User asks for code to be written in Python.",
        "input_text": "Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes.",
        "expected_behavior": "The agent should route to the engineer agent and produce working Python code.",
        "agent_expected": "engineer",
        "tool_expected": ["file_write", "code_execute"],
        "pass_criteria": {
            "agent_selected": "engineer",
            "output_contains_code": True,
            "output_not_empty": True,
        },
    },
    {
        "scenario_id": "replay_003",
        "name": "Plan a multi-step project",
        "description": "User asks to plan a complex project with multiple steps.",
        "input_text": "Help me plan a full-stack web application project with user auth, database, and API. Give me a step-by-step plan.",
        "expected_behavior": "The agent should route to the planner agent and produce a structured multi-step plan.",
        "agent_expected": "planner",
        "tool_expected": [],
        "pass_criteria": {
            "agent_selected": "planner",
            "output_has_structure": True,
            "output_not_empty": True,
        },
    },
    {
        "scenario_id": "replay_004",
        "name": "Remember user preference",
        "description": "User asks the system to remember a preference.",
        "input_text": "Remember that I prefer dark mode in all my applications and I use VS Code as my editor.",
        "expected_behavior": "The agent should route to the memory_coordinator and store the preference.",
        "agent_expected": "memory_coordinator",
        "tool_expected": ["memory_store"],
        "pass_criteria": {
            "agent_selected": "memory_coordinator",
            "tool_called": True,
            "output_not_empty": True,
        },
    },
    {
        "scenario_id": "replay_005",
        "name": "Download a file and save it",
        "description": "User asks to download a file from a URL and save it locally.",
        "input_text": "Download the file at https://example.com/data.csv and save it to my downloads folder.",
        "expected_behavior": "The agent should route to the tool_operator and use file/network tools.",
        "agent_expected": "tool_operator",
        "tool_expected": ["file_write", "http_request"],
        "pass_criteria": {
            "agent_selected": "tool_operator",
            "tool_called": True,
            "output_not_empty": True,
        },
    },
]


def run_replay(
    scenario_id: str,
    model: str = "gpt-4o",
    agent_router: Any = None,
) -> dict[str, Any]:
    """Run a single replay scenario through the agent routing system.

    Args:
        scenario_id: The scenario to run (e.g. 'replay_001').
        model: LLM model to use.
        agent_router: Optional callable that takes input_text and returns
                      a dict with 'agent_name' and 'tool_calls'.

    Returns:
        Dict with scenario_id, result, pass/fail, and timing info.
    """
    scenario = next((s for s in SCENARIOS if s["scenario_id"] == scenario_id), None)
    if scenario is None:
        return {"scenario_id": scenario_id, "error": "Scenario not found"}

    start = time.time()
    result: dict[str, Any] = {
        "scenario_id": scenario_id,
        "name": scenario["name"],
        "input_text": scenario["input_text"],
        "agent_selected": None,
        "tools_called": [],
        "output": "",
        "passed": False,
        "latency_ms": 0,
        "details": {},
    }

    try:
        if agent_router is not None:
            route_result = agent_router(scenario["input_text"])
            result["agent_selected"] = route_result.get("agent_name", "")
            result["tools_called"] = route_result.get("tool_calls", [])
            result["output"] = route_result.get("output", "")
        elif chat_completion is not None:
            routing_prompt = (
                f"Given the user request below, which agent should handle it?\n"
                f"Available agents: researcher, engineer, planner, memory_coordinator, tool_operator\n"
                f"Also list any tools that should be called.\n\n"
                f"Request: {scenario['input_text']}\n\n"
                f'Respond with JSON: {{"agent": "<agent_name>", "tools": ["<tool1>", ...], "output": "<draft response>"}}'
            )
            response = chat_completion(
                messages=[{"role": "user", "content": routing_prompt}],
                model=model,
                temperature=0.0,
                max_tokens=500,
            )
            content = response.get("content", "")
            parsed = _parse_route_response(content)
            result["agent_selected"] = parsed.get("agent", "")
            result["tools_called"] = parsed.get("tools", [])
            result["output"] = parsed.get("output", "")
        else:
            result["output"] = "No LLM client or agent router available"
            result["details"]["skip_reason"] = "no_backend"
    except Exception as e:
        result["output"] = f"Error: {e}"
        result["details"]["error"] = str(e)

    elapsed = (time.time() - start) * 1000
    result["latency_ms"] = round(elapsed, 2)

    criteria = scenario["pass_criteria"]
    passed = True
    if "agent_selected" in criteria:
        passed = passed and result["agent_selected"] == criteria["agent_selected"]
    if criteria.get("tool_called"):
        passed = passed and len(result["tools_called"]) > 0
    if criteria.get("output_not_empty"):
        passed = passed and bool(result["output"].strip())

    result["passed"] = passed
    result["expected"] = {
        "agent_expected": scenario["agent_expected"],
        "tool_expected": scenario["tool_expected"],
    }
    return result


def run_all_replays(
    model: str = "gpt-4o",
    agent_router: Any = None,
) -> dict[str, Any]:
    """Run all replay scenarios and return aggregated results.

    Returns:
        Dict with 'results' list, 'total', 'passed', 'failed', and 'pass_rate'.
    """
    results: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        r = run_replay(
            scenario_id=scenario["scenario_id"],
            model=model,
            agent_router=agent_router,
        )
        results.append(r)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    return {
        "results": results,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
    }


def compare_results(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Compare two replay result sets and return a diff.

    Shows regressions (passed->failed), improvements (failed->passed),
    and unchanged results.
    """
    b_map = {r["scenario_id"]: r for r in baseline.get("results", [])}
    c_map = {r["scenario_id"]: r for r in current.get("results", [])}

    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []

    all_ids = set(b_map.keys()) | set(c_map.keys())
    for sid in sorted(all_ids):
        b = b_map.get(sid)
        c = c_map.get(sid)
        if b is None or c is None:
            continue

        b_pass = b.get("passed", False)
        c_pass = c.get("passed", False)

        entry = {
            "scenario_id": sid,
            "name": b.get("name", ""),
            "baseline_passed": b_pass,
            "current_passed": c_pass,
            "latency_change_ms": c.get("latency_ms", 0) - b.get("latency_ms", 0),
        }
        if b_pass and not c_pass:
            regressions.append(entry)
        elif not b_pass and c_pass:
            improvements.append(entry)
        else:
            unchanged.append(entry)

    b_rate = baseline.get("pass_rate", 0.0)
    c_rate = current.get("pass_rate", 0.0)

    return {
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
        "baseline_pass_rate": b_rate,
        "current_pass_rate": c_rate,
        "pass_rate_change": round(c_rate - b_rate, 4),
    }


def _parse_route_response(content: str) -> dict[str, Any]:
    """Parse the LLM routing response into structured data."""
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        parsed = json.loads(content[start:end])
        return {
            "agent": parsed.get("agent", "planner"),
            "tools": parsed.get("tools", []),
            "output": parsed.get("output", ""),
        }
    except (ValueError, json.JSONDecodeError):
        return {"agent": "planner", "tools": [], "output": content}
