"""Memory Coordinator Agent - Memory Manager for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Memory Coordinator. Manage what the system remembers about the user and projects. Given a conversation or task, identify what should be stored, updated, or retrieved. Respond with ONLY JSON: {"memory_updates": {"category": {"key": "value"}}, "relevant_memories": ["memory1", ...], "context_assembly": "assembled context for this task"} Respond with ONLY valid JSON — no markdown, no code blocks. Use escaped newlines (\\n) in string values, never triple quotes."""


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


def coordinate_memory(task_text: str, existing_memory: dict = None, model: str = None) -> dict:
    """Coordinate memory management for a task.

    Args:
        task_text: The task or conversation to analyze for memory operations.
        existing_memory: Current memory state to consider.
        model: Optional model override.

    Returns:
        dict with memory_updates, relevant_memories, and context_assembly.
    """
    prompt = f"Analyze this task and determine what should be remembered or retrieved:\n\n{task_text}"
    if existing_memory:
        prompt += f"\n\nExisting memory:\n{json.dumps(existing_memory, indent=2)}"

    response = llm_call(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.3,
        max_tokens=1000,
    )
    return _extract_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memory Coordinator Agent")
    parser.add_argument("task", nargs="?", help="Task to analyze for memory")
    parser.add_argument("--memory", help="Existing memory as JSON string")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.task:
        existing = json.loads(args.memory) if args.memory else None
        result = coordinate_memory(args.task, existing_memory=existing, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python memory_coordinator.py \"your task here\"")
