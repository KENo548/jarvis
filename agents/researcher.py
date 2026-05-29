"""Researcher Agent — Searches the web and summarizes findings."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from llm_client import llm_call

AGENT_AGENTS = Path(__file__).resolve().parent


def _load_config() -> dict:
    p = AGENT_AGENTS / "researcher" / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def research_topic(topic: str) -> dict[str, Any]:
    """Research a topic and return structured findings."""
    config = _load_config()
    system = config.get("prompt_template", "You are the SAGE Researcher Agent.")

    prompt = f"""Research this topic and provide a comprehensive summary.

Topic: {topic}

Respond with ONLY a JSON object:
{{
  "summary": "Clear, concise summary of the topic",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "sources": ["source description 1", "source description 2"]
}}

Be factual and cite sources where possible."""

    try:
        response = llm_call(prompt, system=system, temperature=0.3, max_tokens=1024)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        if "summary" not in result:
            result = {"summary": "Research completed.", "key_findings": [], "sources": []}
        return result
    except Exception:
        return {"summary": "Research failed.", "key_findings": [], "sources": []}
