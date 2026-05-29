"""Memory Coordinator Agent — Manages and queries long-term memory."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from llm_client import llm_call

AGENT_AGENTS = Path(__file__).resolve().parent
MEMORY_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "memory_store.json"


def _load_config() -> dict:
    p = AGENT_AGENTS / "orchestrator" / "config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _load_memory() -> dict:
    """Load memory from Chroma (primary) or JSON fallback."""
    try:
        from chroma_client import ChromaClient
        client = ChromaClient()
        if not client.health():
            raise ConnectionError("Chroma unavailable")
        count = client.count()
        return {"chroma_items": count}
    except Exception:
        if MEMORY_PATH.exists():
            return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        return {}


def _store_memory(category: str, key: str, value: str):
    """Store a memory entry in Chroma (primary) with JSON fallback."""
    try:
        from chroma_client import ChromaClient
        client = ChromaClient()
        if not client.health():
            raise ConnectionError("Chroma unavailable")
        # Chroma needs embeddings - use a simple zero vector as placeholder
        # In production, use an embedding model
        embedding = [0.0] * 384
        client.add(
            ids=[f"mem_{uuid.uuid4().hex[:12]}"],
            documents=[f"{category}/{key}: {value}"],
            metadatas=[{"category": category, "key": key}],
            embeddings=[embedding],
        )
    except Exception:
        memory_path = MEMORY_PATH
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if memory_path.exists():
            existing = json.loads(memory_path.read_text(encoding="utf-8"))
        if category not in existing:
            existing[category] = {}
        existing[category][key] = {"value": value}
        memory_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def coordinate_memory(task_text: str) -> dict[str, Any]:
    """Analyze a task and determine if memory should be updated or retrieved."""
    config = _load_config()
    system = (
        "You are the SAGE Memory Coordinator. "
        "Analyze user input to determine if it should be stored in memory "
        "or if existing memory should be retrieved."
    )

    memory = _load_memory()
    memory_summary = json.dumps(memory, indent=2)[:2000] if memory else "No memory stored yet."

    prompt = f"""Analyze this user input and decide what memory action to take.

User input: {task_text}

Current memory:
{memory_summary}

Respond with ONLY a JSON object:
{{
  "action": "store|retrieve|none",
  "memory_updates": {{"category": {{"key": "value"}}}},
  "context_assembly": "Summary of relevant memory for this request"
}}

If the user reveals personal info (name, preferences, etc), set action="store".
If the user asks about something they told you before, set action="retrieve".
If neither applies, set action="none" and memory_updates={{}}."""

    try:
        response = llm_call(prompt, system=system, temperature=0.1, max_tokens=512)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        if "memory_updates" not in result:
            result["memory_updates"] = {}
        if "context_assembly" not in result:
            result["context_assembly"] = ""

        # Execute memory stores
        if result.get("action") == "store" and result.get("memory_updates"):
            for category, entries in result["memory_updates"].items():
                if isinstance(entries, dict):
                    for key, value in entries.items():
                        _store_memory(category, key, str(value))

        return result
    except Exception:
        return {"memory_updates": {}, "context_assembly": "Memory analysis failed."}
