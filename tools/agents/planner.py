"""Planner Agent - Task Decomposer for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Planner agent. Break complex tasks into clear, sequential steps. Each step should be actionable and specific.

IMPORTANT: Your response should be helpful and complete. Not just a list of steps, but a clear plan the user can follow.

Respond with ONLY JSON: {"steps": [{"step": 1, "description": "what to do", "agent": "which agent handles it", "dependencies": []}], "summary": "brief summary of the plan"}
Respond with ONLY valid JSON — no markdown, no code blocks. Use escaped newlines (\\n) in string values, never triple quotes."""


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


def create_plan(task_text: str, model: str = None) -> dict:
    """Create a step-by-step plan for a task.

    Args:
        task_text: The task to decompose into steps.
        model: Optional model override.

    Returns:
        dict with steps list containing step details.
    """
    response = llm_call(
        prompt=f"Break this task into clear, actionable steps:\n\n{task_text}",
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.3,
        max_tokens=1000,
    )
    return _extract_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Planner Agent - Task Decomposer")
    parser.add_argument("task", nargs="?", help="Task to plan")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.task:
        result = create_plan(args.task, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python planner.py \"your task here\"")
