"""Engineer Agent — Writes, edits, and debugs code."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from llm_client import llm_call

AGENT_AGENTS = Path(__file__).resolve().parent


def _load_config() -> dict:
    p = AGENT_AGENTS / "coder" / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def generate_code(description: str) -> dict[str, Any]:
    """Generate code based on a natural language description."""
    config = _load_config()
    system = config.get("prompt_template", "You are the SAGE Engineer Agent.")

    prompt = f"""Write code for this task. Include an explanation and the code itself.

Task: {description}

Respond with ONLY a JSON object:
{{
  "explanation": "Brief explanation of what the code does",
  "code": "the actual code here",
  "language": "python|javascript|bash|etc"
}}

Write clean, working code. No markdown wrapping around the code field."""

    try:
        response = llm_call(prompt, system=system, temperature=0.3, max_tokens=2048)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        if "code" not in result:
            result = {"explanation": "Code generation failed.", "code": "", "language": "python"}
        return result
    except Exception:
        return {"explanation": "Code generation failed.", "code": "", "language": "python"}
