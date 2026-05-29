#!/usr/bin/env python3
"""Gemini -> Ollama bridge for Mark XXXIX tools.

Replaces google.generativeai calls with SAGE's llm_client.
Drop-in replacement: same function signatures, different backend.

Usage:
    from gemini_bridge import generate_text, generate_text_with_system
    response = generate_text("What is 2+2?")
    response = generate_text_with_system("You are a coding assistant", "Write a hello world")
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_client import llm_call, LLMResponse


def generate_text(
    prompt: str,
    model: str | None = None,
    system_instruction: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """Replace genai.GenerativeModel.generate_content().

    Returns just the text response string.
    """
    response = llm_call(
        prompt=prompt,
        model=model,
        system=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.text


def generate_json(
    prompt: str,
    model: str | None = None,
    system_instruction: str = "",
    temperature: float = 0.3,
) -> dict:
    """Generate text and parse as JSON. Returns parsed dict or fallback."""
    text = generate_text(
        prompt=prompt,
        model=model,
        system_instruction=system_instruction,
        temperature=temperature,
    )
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code blocks
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"raw_text": text}


def generate_code(
    description: str,
    language: str = "python",
    model: str | None = None,
) -> str:
    """Generate code for a description. Returns clean code string."""
    system = (
        f"You are an expert {language} developer. "
        f"Write clean, complete, working {language} code. "
        f"Return ONLY the code. No explanation, no markdown, no backticks."
    )
    text = generate_text(
        prompt=f"Write {language} code to accomplish this:\n\n{description}",
        model=model,
        system_instruction=system,
        temperature=0.2,
    )
    # Strip markdown fences
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def generate_with_vision(
    prompt: str,
    image_data: bytes,
    mime_type: str = "image/png",
    model: str | None = None,
) -> str:
    """Generate text from image + prompt.

    NOTE: This uses OpenAI gpt-4o for vision since Ollama vision models
    are weak. Falls back to Ollama if OpenAI is unavailable.
    """
    import base64
    import urllib.request
    import urllib.error

    # Try OpenAI vision first
    try:
        from vault_client import VaultClient
        vc = VaultClient()
        secret = vc.read_secret("jarvis/openai-api-key")
        api_key = secret.value if secret else ""
    except Exception:
        api_key = ""

    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")

    if api_key:
        # Use OpenAI gpt-4o for vision
        b64 = base64.b64encode(image_data).decode()
        body = json.dumps({
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Fallback: Ollama (won't have vision but won't crash)
    return generate_text(
        prompt=f"[Image analysis unavailable — Ollama does not support vision]\n{prompt}",
        model=model,
    )


# ---------------------------------------------------------------------------
# Gemini-compatible class interface (for code that uses genai.GenerativeModel)
# ---------------------------------------------------------------------------

class GeminiCompat:
    """Drop-in replacement for genai.GenerativeModel.

    Usage:
        model = GeminiCompat("gemini-2.5-flash")
        response = model.generate_content("What is 2+2?")
        print(response.text)
    """

    def __init__(self, model_name: str = "", system_instruction: str = ""):
        self.model_name = model_name
        self.system_instruction = system_instruction

    def generate_content(self, prompt: str):
        """Gemini-compatible generate_content interface."""
        text = generate_text(
            prompt=prompt,
            system_instruction=self.system_instruction,
        )
        return _GeminiResponse(text)


class _GeminiResponse:
    """Gemini-compatible response object."""

    def __init__(self, text: str):
        self.text = text


class GeminiClient:
    """Drop-in replacement for genai.Client(api_key=...).

    Usage:
        client = GeminiClient(api_key="ignored")
        model = client.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("What is 2+2?")
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key  # ignored — we use Ollama

    def GenerativeModel(self, model_name: str = "", system_instruction: str = ""):
        """Return a GeminiCompat that acts like GenerativeModel."""
        return GeminiCompat(model_name, system_instruction)
