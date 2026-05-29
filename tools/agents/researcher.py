"""Researcher Agent - Information Retriever for SAGE AI ecosystem."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import llm_call

SYSTEM_PROMPT = """You are Sage, a helpful and knowledgeable AI assistant. You provide comprehensive, warm, and conversational responses.

CRITICAL RULES:
- NEVER give one-line answers. Always provide FULL, HELPFUL responses.
- For greetings: Respond warmly. "Hello! I'm Sage. How can I help you today?"
- For questions like "what is X" or "tell me about Y": Give a complete explanation with context, examples, and interesting details.
- For research tasks: Provide thorough summaries with key findings, actionable insights, and context.
- Be conversational and friendly, like a knowledgeable friend, not a search engine.
- Use natural language with good flow. Not just bullet points.
- If you know something well, share that knowledge generously.

Examples of GOOD responses:
- "Hello! I'm Sage, your AI assistant. I can help you with research, planning, coding, and much more. What would you like to work on today?"
- For "The Big Bang Theory": "The Big Bang Theory is a popular American sitcom that aired on CBS from 2007 to 2019. It follows the lives of two physicists, Sheldon Cooper and Leonard Hofstadter, and their friends. The show became one of the most-watched comedies on television, known for its geek humor and the dynamic between the characters. It ran for 12 seasons and spawned the spinoff Young Sheldon..."

Respond with ONLY JSON: {"summary": "your FULL helpful response here", "key_findings": ["finding1", ...], "sources": [], "confidence": 0.0-1.0}
The summary field is what the user sees — make it complete and helpful.
Respond with ONLY valid JSON — no markdown, no code blocks. Use escaped newlines (\\n) in string values, never triple quotes."""


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
