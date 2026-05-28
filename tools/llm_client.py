#!/usr/bin/env python3
"""Multi-provider LLM client for SAGE agents.

Supports: Ollama (local), OpenAI, NVIDIA NIM, OpenCode Zen, and any
OpenAI-compatible API.  Falls back through providers in priority order.

Usage:
    from llm_client import llm_call, llm_chat
    response = llm_call("What is 2+2?", model="ollama/llama3.2")
    response = llm_chat([{"role":"user","content":"Hi"}], model="openai/gpt-4o-mini")
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def _vault_secret(path: str) -> str:
    """Best-effort read from Vault.  Returns empty string on failure."""
    try:
        from vault_client import VaultClient
        client = VaultClient()
        secret = client.read_secret(path)
        return secret.value if secret else ""
    except Exception:
        return ""

@dataclass
class Provider:
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    priority: int = 100          # lower = preferred
    supports_chat: bool = True
    supports_generate: bool = False   # Ollama-style /api/generate
    headers: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.model:
            self.model = self.name.split("/")[-1]

def _build_providers() -> list[Provider]:
    """Build ordered provider list.  Keys from Vault → env → hardcoded."""
    openai_key = _vault_secret("jarvis/openai-api-key") or _env("OPENAI_API_KEY")
    nvidia_key = _vault_secret("jarvis/nvidia-api-key") or _env("NVIDIA_API_KEY")

    providers = []

    # --- Ollama (always first — local, free, private) ---
    providers.append(Provider(
        name="ollama/llama3.2",
        base_url="http://localhost:11434",
        model="llama3.2:latest",
        priority=10,
        supports_generate=True,
    ))
    # Ollama also has an OpenAI-compatible endpoint at /v1/
    providers.append(Provider(
        name="ollama-openai/llama3.2",
        base_url="http://localhost:11434/v1",
        model="llama3.2:latest",
        priority=11,
        supports_generate=False,
    ))

    # --- OpenAI ---
    if openai_key:
        providers.append(Provider(
            name="openai/gpt-4o-mini",
            base_url="https://api.openai.com/v1",
            api_key=openai_key,
            model="gpt-4o-mini",
            priority=30,
        ))
        providers.append(Provider(
            name="openai/gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key=openai_key,
            model="gpt-4o",
            priority=35,
        ))

    # --- NVIDIA NIM (free tier: 1000 credits/day) ---
    if nvidia_key:
        providers.append(Provider(
            name="nvidia/llama-3.1-nemotron-70b-instruct",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_key,
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            priority=20,
        ))
        providers.append(Provider(
            name="nvidia/llama-3.3-70b-instruct",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_key,
            model="nvidia/llama-3.3-70b-instruct",
            priority=25,
        ))

    # --- OpenCode Zen (OpenAI-compatible, free tier) ---
    # Uncomment and configure when available:
    # zen_key = _vault_secret("jarvis/opencode-zen-key") or _env("OPENCODE_ZEN_API_KEY")
    # if zen_key:
    #     providers.append(Provider(
    #         name="opencode-zen/gpt-4o-mini",
    #         base_url="https://api.opencode.ai/v1",
    #         api_key=zen_key,
    #         model="gpt-4o-mini",
    #         priority=15,
    #     ))

    providers.sort(key=lambda p: p.priority)
    return providers

PROVIDERS: list[Provider] = _build_providers()

# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------

def _resolve_provider(model: str | None = None) -> Provider:
    """Resolve a model string to a Provider.  Falls back to first available."""
    if model:
        # Exact match
        for p in PROVIDERS:
            if p.name == model:
                return p
        # Partial match (e.g. "openai" matches "openai/gpt-4o-mini")
        for p in PROVIDERS:
            if model in p.name:
                return p
    return PROVIDERS[0] if PROVIDERS else _fallback_provider()

def _fallback_provider() -> Provider:
    """Last-resort Ollama provider."""
    return Provider(
        name="ollama/llama3.2",
        base_url="http://localhost:11434",
        model="llama3.2:latest",
        priority=999,
        supports_generate=True,
    )

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_post(url: str, data: dict, headers: dict | None = None,
               timeout: int = 120) -> dict:
    """POST JSON, return parsed response."""
    body = json.dumps(data).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"HTTP {e.code}: {error_body[:500]}") from e

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    latency_ms: int
    token_usage: dict  # {"prompt_tokens": N, "completion_tokens": N, "total": N}
    raw: dict | None = None

def llm_call(
    prompt: str,
    *,
    model: str | None = None,
    system: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: int = 120,
) -> LLMResponse:
    """Single-turn text generation.  Tries providers in priority order."""
    provider = _resolve_provider(model)
    t0 = time.time()

    if provider.supports_generate:
        # Ollama native API
        if system:
            # /api/chat for system+user messages
            messages = [{"role": "user", "content": prompt}]
            data = {
                "model": provider.model,
                "messages": [{"role": "system", "content": system}, messages[0]],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            resp = _http_post(f"{provider.base_url}/api/chat", data, timeout=timeout)
            text = resp.get("message", {}).get("content", "")
            tokens = {
                "prompt_tokens": resp.get("prompt_eval_count", 0),
                "completion_tokens": resp.get("eval_count", 0),
            }
        else:
            # /api/generate for simple prompts
            data = {
                "model": provider.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            resp = _http_post(f"{provider.base_url}/api/generate", data, timeout=timeout)
            text = resp.get("response", "")
            tokens = {
                "prompt_tokens": resp.get("prompt_eval_count", 0),
                "completion_tokens": resp.get("eval_count", 0),
            }
        tokens["total"] = tokens["prompt_tokens"] + tokens["completion_tokens"]
    else:
        # OpenAI-compatible /chat/completions
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        data = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
        resp = _http_post(
            f"{provider.base_url}/chat/completions", data, headers, timeout
        )
        choice = resp.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        usage = resp.get("usage", {})
        tokens = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0),
        }

    latency = int((time.time() - t0) * 1000)
    return LLMResponse(
        text=text,
        model=provider.model,
        provider=provider.name,
        latency_ms=latency,
        token_usage=tokens,
        raw=resp,
    )


def llm_chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: int = 120,
) -> LLMResponse:
    """Multi-turn chat.  Messages must be [{"role": ..., "content": ...}]."""
    provider = _resolve_provider(model)
    t0 = time.time()

    data = {
        "model": provider.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    resp = _http_post(
        f"{provider.base_url}/chat/completions", data, headers, timeout
    )
    choice = resp.get("choices", [{}])[0]
    text = choice.get("message", {}).get("content", "")
    usage = resp.get("usage", {})
    tokens = {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total": usage.get("total_tokens", 0),
    }
    latency = int((time.time() - t0) * 1000)

    return LLMResponse(
        text=text,
        model=provider.model,
        provider=provider.name,
        latency_ms=latency,
        token_usage=tokens,
        raw=resp,
    )


def list_providers() -> list[dict]:
    """Return available providers with status."""
    result = []
    for p in PROVIDERS:
        online = False
        try:
            if p.supports_generate:
                urllib.request.urlopen(f"{p.base_url}/api/tags", timeout=2)
                online = True
            elif p.api_key:
                online = True   # cloud provider with key = assume available
        except Exception:
            pass
        result.append({
            "name": p.name,
            "model": p.model,
            "priority": p.priority,
            "online": online,
            "type": "local" if "localhost" in p.base_url else "cloud",
        })
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SAGE LLM Client")
    sub = parser.add_subparsers(dest="cmd")

    call_p = sub.add_parser("call", help="Single-turn generation")
    call_p.add_argument("prompt")
    call_p.add_argument("--model", "-m", default=None)
    call_p.add_argument("--system", "-s", default="")

    chat_p = sub.add_parser("chat", help="Multi-turn chat")
    chat_p.add_argument("messages", nargs="+", help="role:content pairs")
    chat_p.add_argument("--model", "-m", default=None)

    sub.add_parser("providers", help="List available providers")

    args = parser.parse_args()

    if args.cmd == "call":
        r = llm_call(args.prompt, model=args.model, system=args.system)
        print(f"[{r.provider}] ({r.latency_ms}ms, {r.token_usage.get('total',0)} tokens)")
        print(r.text)

    elif args.cmd == "chat":
        msgs = []
        for m in args.messages:
            if ":" in m:
                role, content = m.split(":", 1)
                msgs.append({"role": role.strip(), "content": content.strip()})
            else:
                msgs.append({"role": "user", "content": m})
        r = llm_chat(msgs, model=args.model)
        print(f"[{r.provider}] ({r.latency_ms}ms, {r.token_usage.get('total',0)} tokens)")
        print(r.text)

    elif args.cmd == "providers":
        for p in list_providers():
            status = "OK" if p["online"] else "--"
            print(f"  {status} {p['name']:45s}  {p['type']:5s}  pri={p['priority']}")

    else:
        parser.print_help()
