"""Commander Agent - Task Router for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Commander agent in the SAGE system. Your job is to analyze a user task and determine which specialist agent should handle it. You have these agents: planner, engineer, researcher, memory_coordinator, tool_operator. Analyze the task and respond with ONLY a JSON object: {"selected_agent": "agent_name", "confidence": 0.0-1.0, "reasoning": "brief explanation", "task_type": "one of: planning, coding, research, memory, tool_use, mixed"} Respond with ONLY valid JSON — no markdown, no code blocks. Use escaped newlines (\\n) in string values, never triple quotes."""


def _extract_json(text: str) -> dict:
    """Extract JSON from text, handling markdown code blocks and nested quotes."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        candidate = text[brace_start:brace_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    pattern = r"```(?:json)?\s*\n(.*?)\n\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {"raw_text": text}


def route_task(task_text: str, model: str = None) -> dict:
    """Route a task to the appropriate specialist agent.

    Args:
        task_text: The user task to analyze and route.
        model: Optional model override.

    Returns:
        dict with selected_agent, confidence, reasoning, and task_type.
    """
    response = llm_call(
        prompt=f"Analyze this task and determine which agent should handle it:\n\n{task_text}",
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.3,
        max_tokens=500,
    )
    return _extract_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Commander Agent - Task Router")
    parser.add_argument("task", nargs="?", help="Task to route")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.task:
        result = route_task(args.task, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python commander.py \"your task here\"")
