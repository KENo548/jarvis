"""Researcher Agent - Information Retriever for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are the Researcher agent. Synthesize information and provide well-structured research summaries. Be thorough but concise. Cite sources when possible. Respond with ONLY JSON: {"summary": "research summary", "key_findings": ["finding1", ...], "sources": [], "confidence": 0.0-1.0} Respond with ONLY valid JSON — no markdown, no code blocks. Use escaped newlines (\\n) in string values, never triple quotes."""


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


def research_topic(query: str, context: str = "", model: str = None) -> dict:
    """Research a topic and provide a structured summary.

    Args:
        query: The research question or topic.
        context: Additional context or existing knowledge.
        model: Optional model override.

    Returns:
        dict with summary, key_findings, sources, and confidence.
    """
    prompt = f"Research this topic and provide a structured summary:\n\n{query}"
    if context:
        prompt += f"\n\nAdditional context:\n{context}"

    response = llm_call(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.4,
        max_tokens=1500,
    )
    return _extract_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Researcher Agent - Information Retriever")
    parser.add_argument("query", nargs="?", help="Topic to research")
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()

    if args.query:
        result = research_topic(args.query, context=args.context, model=args.model)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python researcher.py \"your research question here\"")
