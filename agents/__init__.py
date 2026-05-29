"""SAGE Agents — JSON-config-driven agent modules.

Each agent loads its config from agents/<name>/config.json and uses
the LLM client to execute tasks. No hardcoded prompts — everything
comes from the JSON config.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AGENTS_DIR = Path(__file__).resolve().parent


def load_agent_config(agent_name: str) -> dict[str, Any]:
    """Load config.json for a named agent."""
    config_path = AGENTS_DIR / agent_name / "config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def run_agent(agent_name: str, task: str, *, extra_context: str = "") -> str:
    """Run a task through the named agent's LLM pipeline."""
    import sys
    sys.path.insert(0, str(AGENTS_DIR.parent / "tools"))
    from llm_client import llm_call

    config = load_agent_config(agent_name)
    if not config:
        return f"Agent '{agent_name}' not configured."

    system = config.get("prompt_template", "")
    if extra_context:
        system += f"\n\n{extra_context}"

    response = llm_call(task, system=system, model=config.get("model"))
    return response.text
