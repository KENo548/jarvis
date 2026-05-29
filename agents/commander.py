"""Commander Agent — Routes tasks to the right specialist agent.

Reads its config from agents/orchestrator/config.json.
"""

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


AVAILABLE_AGENTS = {
    "planner": "Creates step-by-step plans for complex goals",
    "engineer": "Writes, edits, and debugs code",
    "researcher": "Searches the web and summarizes findings",
    "memory_coordinator": "Manages and queries long-term memory",
    "tool_operator": "Executes tools like app launcher, browser, files, OS control",
}


def route_task(task_text: str) -> dict[str, Any]:
    """Route a user task to the appropriate agent using LLM classification."""
    config = _load_config()
    system = config.get("prompt_template", "You are the SAGE Orchestrator.")

    agent_list = "\n".join(f"  - {k}: {v}" for k, v in AVAILABLE_AGENTS.items())
    prompt = f"""Classify this user request and select the best agent.

Available agents:
{agent_list}

User request: {task_text}

Respond with ONLY a JSON object:
{{"selected_agent": "<agent_name>", "confidence": <0.0-1.0>, "reasoning": "<brief>"}}

Rules:
- If the user wants to plan something complex → "planner"
- If the user wants code written/fixed/reviewed → "engineer"
- If the user wants information/research → "researcher"
- If the user asks to remember/forget/recall something → "memory_coordinator"
- If the user wants to open apps, control browser, manage files, change settings → "tool_operator"
- For greetings, questions, or anything else → "tool_operator"
"""

    try:
        response = llm_call(prompt, system=system, temperature=0.1, max_tokens=256)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        if "selected_agent" not in result:
            result = {"selected_agent": "tool_operator", "confidence": 0.5, "reasoning": "default"}
        return {
            "selected_agent": result["selected_agent"],
            "route": {
                "model": response.model,
                "provider": response.provider,
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
            },
        }
    except Exception:
        return {
            "selected_agent": "tool_operator",
            "route": {"model": "fallback", "provider": "none", "confidence": 0.0, "reasoning": "routing failed"},
        }
