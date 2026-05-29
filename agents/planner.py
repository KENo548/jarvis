"""Planner Agent — Breaks goals into step-by-step plans."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from llm_client import llm_call

AGENT_AGENTS = Path(__file__).resolve().parent


def _load_config() -> dict:
    p = AGENT_AGENTS / "planner" / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def create_plan(goal: str, context: str = "") -> dict[str, Any]:
    """Create a structured plan for achieving a goal."""
    config = _load_config()
    system = config.get("prompt_template", "You are the SAGE Planner Agent.")

    prompt = f"""Create a step-by-step plan for this goal.

Goal: {goal}
{f'Context: {context}' if context else ''}

Respond with ONLY a JSON object:
{{
  "steps": [
    {{"step": 1, "description": "...", "tool": "optional_tool_name", "risk": "low|medium|high"}},
    ...
  ],
  "summary": "Brief overall summary of the plan"
}}

Limit to 10 steps maximum. Be practical and concise."""

    try:
        response = llm_call(prompt, system=system, temperature=0.3, max_tokens=1024)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        if "steps" not in result:
            result = {"steps": [], "summary": result.get("summary", "No plan generated.")}
        return result
    except Exception:
        return {"steps": [], "summary": "Planning failed. Please try again."}
