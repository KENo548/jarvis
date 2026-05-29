"""Tool Operator Agent — Plans and executes tool calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from llm_client import llm_call

AGENT_AGENTS = Path(__file__).resolve().parent


def _load_config() -> dict:
    p = AGENT_AGENTS / "orchestrator" / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


AVAILABLE_TOOLS = {
    "open_app": "Opens applications on the computer",
    "browser_control": "Controls web browsers (navigate, click, type, scroll)",
    "file_controller": "Manages files and folders (list, create, delete, move, copy)",
    "computer_control": "Direct computer control (type, click, hotkeys, scroll, mouse)",
    "computer_settings": "System settings (volume, brightness, WiFi, dark mode, power)",
    "web_search": "Searches the web for information",
    "screen_process": "Captures and analyzes screen or webcam",
    "code_helper": "Writes, edits, explains, runs code",
    "file_processor": "Processes uploaded files (images, PDFs, CSVs, etc)",
    "weather_report": "Gets weather information",
    "reminder": "Sets timed reminders",
    "send_message": "Sends messages via messaging platforms",
    "youtube_video": "Controls YouTube (play, summarize, trending)",
    "desktop_control": "Desktop management (wallpaper, organize, clean)",
    "game_updater": "Steam/Epic game management",
    "flight_finder": "Searches Google Flights",
}


def plan_tool_usage(task_text: str) -> dict[str, Any]:
    """Plan which tools to call for a user request."""
    config = _load_config()
    system = config.get("prompt_template", "You are the SAGE Tool Operator.")

    tool_list = "\n".join(f"  - {k}: {v}" for k, v in AVAILABLE_TOOLS.items())
    prompt = f"""Analyze this user request and decide which tools to call.

Available tools:
{tool_list}

User request: {task_text}

Respond with ONLY a JSON object:
{{
  "tool_calls": [
    {{"tool": "tool_name", "params": {{"action": "...", ...}}}}
  ],
  "response": "Brief conversational response if no tools needed, or description of what will be executed"
}}

Rules:
- If no tool is needed, return tool_calls as empty array and put a conversational response.
- For simple questions/conversation, respond directly without tools.
- Each tool call must have the correct parameter schema for that tool.
- For open_app: {{"tool": "open_app", "params": {{"app_name": "Calculator"}}}}
- For browser: {{"tool": "browser_control", "params": {{"action": "go_to", "url": "https://google.com"}}}}
- For files: {{"tool": "file_controller", "params": {{"action": "list", "path": "desktop"}}}}
"""

    try:
        response = llm_call(prompt, system=system, temperature=0.1, max_tokens=1024)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        if "tool_calls" not in result:
            result["tool_calls"] = []
        if "response" not in result:
            result["response"] = ""
        return result
    except Exception:
        return {"tool_calls": [], "response": "I couldn't process that request. Could you rephrase?"}
