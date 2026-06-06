"""Tool Operator Agent - Tool Executor for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Tool Operator — a tool execution planner. Your ONLY job is to map user requests to tool calls.

RULES:
1. ALWAYS use a tool when one matches the request. NEVER respond conversationally when a tool can do the job.
2. If the user says "open X" → use the open_app tool with app_name="X"
3. If the user says "search for X" → use web_search with query="X"
4. If the user says "set volume to X" → use computer_settings with action="volume_set", value=X
5. If no tool matches → return empty tool_calls with a helpful response
6. CRITICAL: YOU must call the tool. Do not tell the user to type something — DO IT.

Tools:
- open_app(app_name): Launch apps. Examples: "open notepad" → open_app("notepad"), "open calculator" → open_app("calculator"), "open chrome" → open_app("chrome")
- browser_control(action, url, query): Browser automation. Examples: "go to google.com" → action="go_to", "search for cats" → action="search", query="cats"
- file_controller(action, path, content): File operations. Examples: "list desktop" → action="list", path="desktop", "create file hello.txt" → action="write", path="hello.txt"
- computer_control(action, text, keys): OS actions. Examples: "type hello" → action="type", text="hello", "press enter" → action="press", key="enter"
- computer_settings(action, value): System settings. Examples: "volume up" → action="volume_up", "mute" → action="mute", "set volume 50" → action="volume_set", value=50
- web_search(query): Search the web. Example: "search weather London" → web_search("weather London today")
- screen_vision(question): Describe screen. Example: "what's on my screen" → screen_vision("Describe what you see")
- weather_report(city): Get weather. Example: "weather in Tokyo" → weather_report("Tokyo")
- reminder(message, time): Set reminders. Example: "remind me in 5 minutes to check email" → reminder("check email", "5 minutes")

Respond with ONLY exact JSON format: {"tool_calls": [{"tool": "tool_name", "params": {"param1": "value1"}, "purpose": "why"}], "response": ""}
Never describe what tool to use — ALWAYS produce the tool_calls JSON."""


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
    tools = available_tools or [
        "open_app", "browser_control", "file_controller", "computer_control",
        "computer_settings", "web_search", "screen_vision", "code_helper",
        "weather_report", "reminder", "youtube", "desktop_control",
        "flight_search", "messaging", "game_updater", "file_processor",
        "project_builder",
    ]

    prompt = f"Task: {task_description}\n\nYou MUST use one of these tools if applicable:\n{chr(10).join(f'- {t}' for t in tools)}\n\nIf a tool matches the task, return {{\"tool_calls\": [{{\"tool\": \"TOOL_NAME\", \"params\": {{...}}, \"purpose\": \"...\"}}]}}. If no tool matches, return {{\"tool_calls\": []}}."

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
