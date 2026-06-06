"""Memory Coordinator Agent — Manages and queries long-term memory.

Uses tools/memory_store.py as the single canonical memory backend.
No more duplicate Chroma + JSON fallback paths.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from llm_client import llm_call
from memory_store import store_note, search_notes, list_notes


SYSTEM_PROMPT = """You are the Memory Coordinator. Manage what the system remembers about the user and projects.

Given a conversation or task, identify what should be stored, updated, or retrieved.

Respond with ONLY JSON:
{
  "action": "store|retrieve|none",
  "memory_updates": {"category": {"key": "value"}},
  "context_assembly": "assembled context for this task"
}

Rules:
- If the user reveals personal info (name, preferences, habits, projects) → action="store"
- If the user asks about something they told you before → action="retrieve"
- If neither applies → action="none" and memory_updates={}
- Keep values concise (under 200 chars each)
- Use category names: identity, preferences, projects, relationships, wishes, notes"""

MEMORY_CATEGORIES = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}


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
    import re
    pattern = r"```(?:json)?\s*\n(.*?)\n\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {"raw_text": text}


def _store_memory_updates(memory_updates: dict[str, dict[str, str]]) -> int:
    """Store memory updates into the canonical SQLite + Chroma store.
    
    Returns the number of entries stored.
    """
    count = 0
    for category, entries in memory_updates.items():
        if not isinstance(entries, dict):
            continue
        for key, value in entries.items():
            try:
                store_note(
                    title=f"{category}/{key}",
                    content=str(value)[:200],
                    source_type="memory_coordinator",
                    source_ref=f"category:{category}",
                    tags=[category, key],
                    confidence=0.8,
                )
                count += 1
            except Exception:
                pass
    return count


def _retrieve_memory(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search memory for relevant entries."""
    try:
        notes = search_notes(query, limit=limit)
        return [
            {
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "confidence": note.confidence,
            }
            for note in notes
        ]
    except Exception:
        return []


def _get_memory_summary() -> str:
    """Get a summary of all stored memory."""
    try:
        notes = list_notes(limit=50)
        if not notes:
            return "No memory stored yet."
        lines = []
        for note in notes:
            lines.append(f"- [{note.title}] {note.content[:100]}")
        return "\n".join(lines)
    except Exception:
        return "Memory unavailable."


def coordinate_memory(task_text: str, model: str = None) -> dict[str, Any]:
    """Analyze a task and determine if memory should be updated or retrieved.

    Args:
        task_text: The task or conversation to analyze for memory operations.
        model: Optional model override.

    Returns:
        dict with action, memory_updates, relevant_memories, context_assembly.
    """
    memory_summary = _get_memory_summary()

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
        response = llm_call(prompt, system=SYSTEM_PROMPT, model=model, temperature=0.1, max_tokens=512)
        result = _extract_json(response.text)

        if "action" not in result:
            result["action"] = "none"
        if "memory_updates" not in result:
            result["memory_updates"] = {}
        if "context_assembly" not in result:
            result["context_assembly"] = ""

        # Execute memory stores via canonical backend
        if result.get("action") == "store" and result.get("memory_updates"):
            count = _store_memory_updates(result["memory_updates"])
            if count > 0:
                result["context_assembly"] = f"Stored {count} memory entries. {result.get('context_assembly', '')}"

        # Execute memory retrieval
        if result.get("action") == "retrieve":
            relevant = _retrieve_memory(task_text)
            if relevant:
                result["relevant_memories"] = relevant
                memories_text = "\n".join(
                    f"- {m['title']}: {m['content']}" for m in relevant
                )
                result["context_assembly"] = f"Retrieved memories:\n{memories_text}\n\n{result.get('context_assembly', '')}"

        return result
    except Exception:
        return {"action": "none", "memory_updates": {}, "context_assembly": "Memory analysis failed."}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memory Coordinator Agent")
    parser.add_argument("task", nargs="?", help="Task to analyze for memory")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.task:
        result = coordinate_memory(args.task, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python memory_coordinator.py \"your task here\"")
