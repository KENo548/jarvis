"""Tool Operator Agent - Tool Executor for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Tool Operator. Given a task, determine which tools/commands are needed and produce the exact execution plan.

IMPORTANT RULES:
- If the task is vague or unclear, ask for clarification instead of failing
- If no tools are needed, respond with an empty tool_calls list
- Always provide a helpful response even when no tools are needed

Tools available: shell_command, file_read, file_write, web_search, api_call, docker_exec

Respond with ONLY JSON: {"tool_calls": [{"tool": "tool_name", "params": {}, "purpose": "why"}], "response": "helpful message if no tools needed"}
The "response" field is optional - use it when no tools are needed or to add context.
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


def plan_tool_usage(task_description: str, available_tools: list = None, model: str = None) -> dict:
    """Plan which tools to use for a task.

    Args:
        task_description: Description of what needs to be done.
        available_tools: List of available tool names (defaults to all tools).
        model: Optional model override.

    Returns:
        dict with tool_calls list containing tool, params, and purpose.
    """
    tools = available_tools or ["shell_command", "file_read", "file_write", "web_search", "api_call", "docker_exec"]

    prompt = f"Plan the tool usage for this task:\n\n{task_description}\n\nAvailable tools: {', '.join(tools)}"

    response = llm_call(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.2,
        max_tokens=1000,
    )
    return _extract_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tool Operator Agent")
    parser.add_argument("task", nargs="?", help="Task to plan tools for")
    parser.add_argument("--tools", nargs="+", help="Available tools")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.task:
        result = plan_tool_usage(args.task, available_tools=args.tools, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python tool_operator.py \"your task here\"")
