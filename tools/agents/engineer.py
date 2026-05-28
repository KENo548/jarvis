"""Engineer Agent - Code Generator for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Engineer agent. Write clean, working Python code. When given a task, produce complete, runnable code. Include error handling. Respond with ONLY valid JSON — no markdown, no code blocks. Use escaped newlines (\\n) in string values, never triple quotes. Format: {"code": "the python code with \\n", "language": "python", "explanation": "brief explanation", "files_affected": []}"""


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


def generate_code(task_description: str, context: str = "", model: str = None) -> dict:
    """Generate Python code for a task.

    Args:
        task_description: Description of what code to write.
        context: Additional context or existing code.
        model: Optional model override.

    Returns:
        dict with code, language, explanation, and files_affected.
    """
    prompt = f"Write Python code for this task:\n\n{task_description}"
    if context:
        prompt += f"\n\nContext:\n{context}"

    response = llm_call(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.2,
        max_tokens=2000,
    )
    return _extract_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Engineer Agent - Code Generator")
    parser.add_argument("task", nargs="?", help="Task to generate code for")
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.task:
        result = generate_code(args.task, context=args.context, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python engineer.py \"your coding task here\"")
