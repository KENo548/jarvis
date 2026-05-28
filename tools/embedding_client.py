#!/usr/bin/env python3
"""Embedding backend selection for JARVIS.

Uses Ollama with nomic-embed-text (768-dim) when available, and falls back
to a deterministic local signal when the embedding service is not reachable.

Phase 2 fix: nomic-embed-text is now the primary embedding backend.
The deterministic fallback is only used when Ollama is unreachable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


OLLAMA_DEFAULT_HOST = "http://localhost:11434"
NOMIC_EMBED_MODEL = "nomic-embed-text"
NOMIC_EMBED_DIMS = 768


def _deterministic_embedding(text: str) -> list[float]:
    """Deterministic fallback — NOT a real embedding. Used only when Ollama is down."""
    tokens = [token for token in text.lower().split() if token]
    if not tokens:
        return [0.0] * NOMIC_EMBED_DIMS
    length = float(len(tokens))
    unique = float(len(set(tokens)))
    avg_token_length = sum(len(token) for token in tokens) / length
    base = [length, unique, avg_token_length]
    pad = [0.0] * (NOMIC_EMBED_DIMS - len(base))
    return base + pad


def _ollama_embedding(text: str, host: str, model: str) -> list[float]:
    """Call Ollama /api/embeddings endpoint for real embeddings."""
    payload = {"model": model, "prompt": text}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    embedding = body.get("embedding")
    if not isinstance(embedding, list) or len(embedding) == 0:
        raise ValueError("Ollama embedding response missing or empty embedding vector")
    return [float(value) for value in embedding]


def _check_ollama_health(host: str) -> bool:
    """Quick health check against Ollama /api/tags endpoint."""
    try:
        request = urllib.request.Request(f"{host.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            models = body.get("models", [])
            model_names = [m.get("name", "") for m in models]
            return any(NOMIC_EMBED_MODEL in name for name in model_names)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
        return False


def embed_text(text: str, provider: str | None = None) -> list[float]:
    """Generate an embedding vector for the given text.

    Provider resolution:
      1. Explicit ``provider`` argument
      2. ``EMBEDDING_PROVIDER`` env var  (default: "auto")
      3. "auto" tries Ollama first, falls back to deterministic

    When provider is "ollama" and Ollama is unreachable, raises instead of
    falling back — use "auto" for graceful degradation.
    """
    provider_name = (provider or os.getenv("EMBEDDING_PROVIDER", "auto")).strip().lower()
    host = os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST)
    model = os.getenv("EMBEDDING_MODEL", NOMIC_EMBED_MODEL)

    if provider_name in {"ollama", "auto"}:
        try:
            return _ollama_embedding(text, host=host, model=model)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
            if provider_name == "ollama":
                raise
            # auto: fall through to deterministic

    return _deterministic_embedding(text)


def embedding_backend(provider: str | None = None) -> str:
    """Return the name of the active embedding backend."""
    provider_name = (provider or os.getenv("EMBEDDING_PROVIDER", "auto")).strip().lower()
    if provider_name == "deterministic":
        return "deterministic"
    host = os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST)
    if _check_ollama_health(host):
        return "ollama-nomic-embed-text"
    return "deterministic"


def embedding_dim(provider: str | None = None) -> int:
    """Return the dimensionality of vectors produced by the active backend."""
    backend = embedding_backend(provider)
    if "nomic" in backend:
        return NOMIC_EMBED_DIMS
    return NOMIC_EMBED_DIMS  # deterministic also pads to 768
