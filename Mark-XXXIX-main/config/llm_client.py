import json
import os
import re
import sys
import time
import threading
from pathlib import Path
from typing import Any

import requests

_llm_lock = threading.Lock()


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = _get_base_dir() / "config" / "api_keys.json"

_PROVIDER_ALIASES = {
    "openai": "openai",
    "nvidia": "nvidia",
    "nv": "nvidia",
    "opencode_zen": "opencode_zen",
    "opencode zen": "opencode_zen",
    "opencode": "opencode_zen",
    "zen": "opencode_zen",
}

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "nvidia": "meta/llama-3.1-70b-instruct",
    "opencode_zen": "gpt-4.1-mini",
}

_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "opencode_zen": "",
}

_ENV_KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "opencode_zen": "OPENCODE_ZEN_API_KEY",
}

_CONFIG_KEY_NAMES = {
    "openai": "openai_api_key",
    "nvidia": "nvidia_api_key",
    "opencode_zen": "opencode_zen_api_key",
}

_ENV_BASE_URL_NAMES = {
    "openai": "OPENAI_BASE_URL",
    "nvidia": "NVIDIA_BASE_URL",
    "opencode_zen": "OPENCODE_ZEN_BASE_URL",
}

_CONFIG_BASE_URL_NAMES = {
    "openai": "openai_base_url",
    "nvidia": "nvidia_base_url",
    "opencode_zen": "opencode_zen_base_url",
}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _pretty_model_name(model_id: str) -> str:
    raw = str(model_id or "").split("/")[-1]
    raw = raw.replace("_", " ").replace("-", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return model_id

    words: list[str] = []
    for token in raw.split(" "):
        lower = token.lower()
        if lower == "gpt":
            words.append("GPT")
        elif lower == "qwen":
            words.append("Qwen")
        elif lower == "glm":
            words.append("GLM")
        elif lower == "kimi":
            words.append("Kimi")
        elif lower == "mimo":
            words.append("MiMo")
        elif lower == "llama":
            words.append("Llama")
        elif lower == "nvidia":
            words.append("NVIDIA")
        elif lower == "openai":
            words.append("OpenAI")
        elif token.isdigit() or token.isupper():
            words.append(token)
        else:
            words.append(token[:1].upper() + token[1:])
    return " ".join(words)


def _is_local_base_url(base_url: str) -> bool:
    target = (base_url or "").lower()
    return any(token in target for token in ("localhost", "127.0.0.1", "0.0.0.0"))


def _is_free_model(meta: dict[str, Any], provider: str, base_url: str = "") -> bool:
    if str(meta.get("is_free", "")).lower() in {"1", "true", "yes"}:
        return True
    pricing = meta.get("pricing")
    if isinstance(pricing, dict):
        inputs = " ".join(str(pricing.get(k, "")) for k in ("input", "output", "cached_read", "cached_write"))
        if "free" in inputs.lower():
            return True
    if provider == "nvidia" and not _is_local_base_url(base_url):
        return True
    return False


def _base_model_meta(model_id: str, provider: str) -> dict[str, Any]:
    mid = model_id.lower()
    display_name = _pretty_model_name(model_id)
    context_window: Any = "unknown"
    reasoning = "unknown"
    good_for = "general tasks"
    modalities = ["text"]
    endpoint = "/chat/completions"
    pricing: dict[str, Any] | None = None
    is_free = False

    if provider == "openai":
        if mid.startswith("gpt-5"):
            context_window = 272000
            reasoning = "yes"
            good_for = "high-end reasoning and coding"
            modalities = ["text", "images", "audio"]
            endpoint = "/responses"
        elif mid.startswith("gpt-4.1"):
            context_window = 1000000
            reasoning = "yes"
            good_for = "long-context reasoning and code"
            modalities = ["text", "images"]
            endpoint = "/responses"
        elif mid.startswith("gpt-4o") or mid == "chat-latest":
            context_window = 128000
            reasoning = "partial"
            good_for = "balanced multimodal assistant"
            modalities = ["text", "images", "audio"] if mid == "gpt-4o" else ["text", "images"]
        elif "embedding" in mid:
            context_window = 8192
            reasoning = "no"
            good_for = "text embeddings"
            modalities = ["text"]
        elif "whisper" in mid or "transcribe" in mid:
            context_window = 0
            reasoning = "no"
            good_for = "speech transcription"
            modalities = ["audio"]
        elif mid.startswith("tts-") or "speech" in mid or "audio" in mid:
            context_window = 0
            reasoning = "no"
            good_for = "text to speech"
            modalities = ["text", "audio"]
        elif "image" in mid:
            context_window = 0
            reasoning = "no"
            good_for = "image generation and editing"
            modalities = ["text", "images"]
        elif "search-preview" in mid:
            context_window = 128000
            reasoning = "partial"
            good_for = "search-assisted chat"
            modalities = ["text", "images"]
        else:
            context_window = 32768
            reasoning = "partial"
            good_for = "general chat"
    elif provider == "nvidia":
        if any(token in mid for token in ("bge", "embed", "embedding")):
            context_window = 8192
            reasoning = "no"
            good_for = "text embeddings"
            modalities = ["text"]
        elif any(token in mid for token in ("whisper", "tts", "transcribe", "speaker")):
            context_window = 0
            reasoning = "no"
            good_for = "audio transcription or synthesis"
            modalities = ["audio"] if "tts" in mid or "speak" in mid else ["audio", "text"]
        elif any(token in mid for token in ("fuyu", "deplot", "vision", "vlm", "gemma-3n", "llama-3.2-vision")):
            context_window = 128000
            reasoning = "partial"
            good_for = "multimodal vision tasks"
            modalities = ["text", "images"]
            if "gemma-3n" in mid:
                modalities = ["text", "images", "audio"]
        elif any(token in mid for token in ("code", "coder", "starcoder", "deepseek", "qwen", "llama", "nemotron", "mixtral", "granite", "jamba", "yi", "sea-lion", "dbrx", "seed-oss")):
            context_window = 128000 if any(token in mid for token in ("deepseek-v4", "qwen", "llama-3.1", "llama-3.2", "nemotron", "granite-3", "jamba", "seed-oss")) else 65536
            reasoning = "partial" if any(token in mid for token in ("deepseek", "qwen", "nemotron", "jamba", "granite")) else "no"
            good_for = "coding and general reasoning"
            modalities = ["text"]
        else:
            context_window = 65536
            reasoning = "partial"
            good_for = "general open-model chat"
            modalities = ["text"]
        endpoint = "/chat/completions"

    return {
        "id": model_id,
        "display_name": display_name,
        "context_window": context_window,
        "reasoning": reasoning,
        "good_for": good_for,
        "modalities": modalities,
        "endpoint": endpoint,
        "provider": provider,
    }


def _finalize_model_meta(meta: dict[str, Any], provider: str, base_url: str = "") -> dict[str, Any]:
    model_id = str(meta.get("id") or "").strip()
    provider = _normalize_provider(provider)
    if not model_id:
        return dict(meta)

    data = _base_model_meta(model_id, provider)
    data.update(meta)
    data["id"] = model_id
    data["provider"] = provider
    data["base_url"] = base_url
    data.setdefault("display_name", _pretty_model_name(model_id))
    if provider == "nvidia" and not _is_local_base_url(base_url):
        data.setdefault("pricing", {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"})
        data["is_free"] = True
    return data


def format_model_label(meta: dict[str, Any]) -> str:
    name = str(meta.get("display_name") or meta.get("id") or "unknown")
    if _is_free_model(meta, str(meta.get("provider") or ""), str(meta.get("base_url") or "")):
        return f"{name}  FREE"
    return name


def search_models(models: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    norm = _normalize_text(query)
    if not norm:
        return sorted(
            models,
            key=lambda meta: (
                0 if _is_free_model(meta, str(meta.get("provider") or ""), str(meta.get("base_url") or "")) else 1,
                str(meta.get("display_name") or meta.get("id") or "").lower(),
            ),
        )

    scored: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    for meta in models:
        text = _normalize_text(" ".join([
            str(meta.get("id") or ""),
            str(meta.get("display_name") or ""),
            str(meta.get("good_for") or ""),
            " ".join(str(x) for x in (meta.get("modalities") or [])),
        ]))
        if norm == "free":
            group = 0 if _is_free_model(meta, str(meta.get("provider") or ""), str(meta.get("base_url") or "")) else 2
        elif text.startswith(norm):
            group = 0
        elif norm in text:
            group = 1
        else:
            continue

        free_bias = 0 if _is_free_model(meta, str(meta.get("provider") or ""), str(meta.get("base_url") or "")) else 1
        label = str(meta.get("display_name") or meta.get("id") or "").lower()
        scored.append(((group, free_bias, label), meta))

    if not scored:
        return sorted(
            models,
            key=lambda meta: (
                0 if _is_free_model(meta, str(meta.get("provider") or ""), str(meta.get("base_url") or "")) else 1,
                str(meta.get("display_name") or meta.get("id") or "").lower(),
            ),
        )

    return [meta for _, meta in sorted(scored, key=lambda item: item[0])]

_MODEL_FALLBACKS: dict[str, list[dict[str, Any]]] = {
    "openai": [
        {"id": "gpt-4o", "context_window": 128000, "reasoning": "partial", "good_for": "balanced multimodal assistant", "modalities": ["text", "images", "audio"]},
        {"id": "gpt-4o-mini", "context_window": 128000, "reasoning": "partial", "good_for": "fast low-cost general tasks", "modalities": ["text", "images"]},
        {"id": "gpt-4.1", "context_window": 1000000, "reasoning": "yes", "good_for": "long-context reasoning and coding", "modalities": ["text", "images"]},
        {"id": "gpt-4.1-mini", "context_window": 1000000, "reasoning": "yes", "good_for": "cheap long-context tasks", "modalities": ["text", "images"]},
    ],
    "nvidia": [
        {"id": "meta/llama-3.1-70b-instruct", "context_window": 131072, "reasoning": "no", "good_for": "strong open instruct model", "modalities": ["text"]},
        {"id": "meta/llama-3.1-405b-instruct", "context_window": 131072, "reasoning": "no", "good_for": "highest quality open text generation", "modalities": ["text"]},
        {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "context_window": 131072, "reasoning": "partial", "good_for": "enterprise chat and coding", "modalities": ["text"]},
        {"id": "mistralai/mixtral-8x22b-instruct-v0.1", "context_window": 65536, "reasoning": "no", "good_for": "economical long context text", "modalities": ["text"]},
    ],
    "opencode_zen": [
        {"id": "gpt-4.1-mini", "context_window": 1000000, "reasoning": "yes", "good_for": "general coding and chat", "modalities": ["text", "images"]},
        {"id": "gpt-4o-mini", "context_window": 128000, "reasoning": "partial", "good_for": "low-latency assistant tasks", "modalities": ["text", "images"]},
    ],
}

_ZEN_MODEL_METADATA: dict[str, dict[str, Any]] = {
    "big-pickle": {"display_name": "Big Pickle", "pricing": {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "free experimental model", "modalities": ["text"]},
    "deepseek-v4-flash-free": {"display_name": "DeepSeek V4 Flash Free", "pricing": {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "free fast general usage", "modalities": ["text"]},
    "mimo-v2.5-free": {"display_name": "MiMo-V2.5 Free", "pricing": {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "free general chat/coding", "modalities": ["text"]},
    "nemotron-3-super-free": {"display_name": "Nemotron 3 Super Free", "pricing": {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "free Nvidia-hosted model", "modalities": ["text"]},
    "minimax-m2.7": {"display_name": "MiniMax M2.7", "pricing": {"input": "$0.30", "output": "$1.20", "cached_read": "$0.06", "cached_write": "$0.375"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "cost-efficient coding agent work", "modalities": ["text"]},
    "minimax-m2.5": {"display_name": "MiniMax M2.5", "pricing": {"input": "$0.30", "output": "$1.20", "cached_read": "$0.06", "cached_write": "$0.375"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "budget general purpose model", "modalities": ["text"]},
    "minimax-m2.5-free": {"display_name": "MiniMax M2.5 Free", "pricing": {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "free MiniMax variant", "modalities": ["text"]},
    "glm-5.1": {"display_name": "GLM 5.1", "pricing": {"input": "$1.40", "output": "$4.40", "cached_read": "$0.26", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "strong multilingual reasoning", "modalities": ["text"]},
    "glm-5": {"display_name": "GLM 5", "pricing": {"input": "$1.00", "output": "$3.20", "cached_read": "$0.20", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "balanced multilingual tasks", "modalities": ["text"]},
    "kimi-k2.5": {"display_name": "Kimi K2.5", "pricing": {"input": "$0.60", "output": "$3.00", "cached_read": "$0.10", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "cost-effective long reasoning", "modalities": ["text"]},
    "kimi-k2.6": {"display_name": "Kimi K2.6", "pricing": {"input": "$0.95", "output": "$4.00", "cached_read": "$0.16", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "upgraded Kimi reasoning quality", "modalities": ["text"]},
    "qwen3.6-plus": {"display_name": "Qwen3.6 Plus", "pricing": {"input": "$0.50", "output": "$3.00", "cached_read": "$0.05", "cached_write": "$0.625"}, "endpoint": "/messages", "reasoning": "unknown", "context_window": "unknown", "good_for": "general agent and coding tasks", "modalities": ["text", "images"]},
    "qwen3.6-plus-free": {"display_name": "Qwen3.6 Plus Free", "pricing": {"input": "Free", "output": "Free", "cached_read": "Free", "cached_write": "-"}, "endpoint": "/messages", "reasoning": "unknown", "context_window": "unknown", "good_for": "free Qwen plus tier", "modalities": ["text", "images"]},
    "qwen3.5-plus": {"display_name": "Qwen3.5 Plus", "pricing": {"input": "$0.20", "output": "$1.20", "cached_read": "$0.02", "cached_write": "$0.25"}, "endpoint": "/messages", "reasoning": "unknown", "context_window": "unknown", "good_for": "very low-cost routine tasks", "modalities": ["text", "images"]},
    "grok-build-0.1": {"display_name": "Grok Build 0.1", "pricing": {"input": "$1.00", "output": "$2.00", "cached_read": "$0.20", "cached_write": "-"}, "endpoint": "/chat/completions", "reasoning": "unknown", "context_window": "unknown", "good_for": "code/build style prompts", "modalities": ["text"]},
    "claude-opus-4-8": {"display_name": "Claude Opus 4.8", "pricing": {"input": "$5.00", "output": "$25.00", "cached_read": "$0.50", "cached_write": "$6.25"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "max quality reasoning and coding", "modalities": ["text", "images"]},
    "claude-opus-4-7": {"display_name": "Claude Opus 4.7", "pricing": {"input": "$5.00", "output": "$25.00", "cached_read": "$0.50", "cached_write": "$6.25"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "top-tier complex tasks", "modalities": ["text", "images"]},
    "claude-opus-4-6": {"display_name": "Claude Opus 4.6", "pricing": {"input": "$5.00", "output": "$25.00", "cached_read": "$0.50", "cached_write": "$6.25"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "high-end reasoning", "modalities": ["text", "images"]},
    "claude-opus-4-5": {"display_name": "Claude Opus 4.5", "pricing": {"input": "$5.00", "output": "$25.00", "cached_read": "$0.50", "cached_write": "$6.25"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "high-quality strategic tasks", "modalities": ["text", "images"]},
    "claude-opus-4-1": {"display_name": "Claude Opus 4.1", "pricing": {"input": "$15.00", "output": "$75.00", "cached_read": "$1.50", "cached_write": "$18.75"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "premium difficult reasoning", "modalities": ["text", "images"]},
    "claude-sonnet-4-6": {"display_name": "Claude Sonnet 4.6", "pricing": {"input": "$3.00", "output": "$15.00", "cached_read": "$0.30", "cached_write": "$3.75"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "balanced quality and speed", "modalities": ["text", "images"]},
    "claude-sonnet-4-5": {"display_name": "Claude Sonnet 4.5", "pricing": {"input": "$3.00 (<=200K) / $6.00 (>200K)", "output": "$15.00 (<=200K) / $22.50 (>200K)", "cached_read": "$0.30 (<=200K) / $0.60 (>200K)", "cached_write": "$3.75 (<=200K) / $7.50 (>200K)"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "strong everyday coding agent", "modalities": ["text", "images"]},
    "claude-sonnet-4": {"display_name": "Claude Sonnet 4", "pricing": {"input": "$3.00 (<=200K) / $6.00 (>200K)", "output": "$15.00 (<=200K) / $22.50 (>200K)", "cached_read": "$0.30 (<=200K) / $0.60 (>200K)", "cached_write": "$3.75 (<=200K) / $7.50 (>200K)"}, "endpoint": "/messages", "reasoning": "yes", "context_window": "200K+", "good_for": "legacy balanced sonnet tier", "modalities": ["text", "images"]},
    "claude-haiku-4-5": {"display_name": "Claude Haiku 4.5", "pricing": {"input": "$1.00", "output": "$5.00", "cached_read": "$0.10", "cached_write": "$1.25"}, "endpoint": "/messages", "reasoning": "partial", "context_window": "200K+", "good_for": "fast and affordable responses", "modalities": ["text", "images"]},
    "gemini-3.5-flash": {"display_name": "Gemini 3.5 Flash", "pricing": {"input": "$1.50", "output": "$9.00", "cached_read": "$0.15", "cached_write": "-"}, "endpoint": "/models/{id}", "reasoning": "partial", "context_window": "unknown", "good_for": "fast multimodal tasks", "modalities": ["text", "images", "audio"]},
    "gemini-3.1-pro": {"display_name": "Gemini 3.1 Pro", "pricing": {"input": "$2.00 (<=200K) / $4.00 (>200K)", "output": "$12.00 (<=200K) / $18.00 (>200K)", "cached_read": "$0.20 (<=200K) / $0.40 (>200K)", "cached_write": "-"}, "endpoint": "/models/{id}", "reasoning": "yes", "context_window": "200K+", "good_for": "deeper reasoning and analysis", "modalities": ["text", "images", "audio"]},
    "gemini-3-flash": {"display_name": "Gemini 3 Flash", "pricing": {"input": "$0.50", "output": "$3.00", "cached_read": "$0.05", "cached_write": "-"}, "endpoint": "/models/{id}", "reasoning": "partial", "context_window": "unknown", "good_for": "cost-efficient multimodal", "modalities": ["text", "images", "audio"]},
    "gpt-5.5": {"display_name": "GPT 5.5", "pricing": {"input": "$5.00 (<=272K) / $10.00 (>272K)", "output": "$30.00 (<=272K) / $45.00 (>272K)", "cached_read": "$0.50 (<=272K) / $1.00 (>272K)", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K+", "good_for": "flagship reasoning and coding", "modalities": ["text", "images", "audio"]},
    "gpt-5.5-pro": {"display_name": "GPT 5.5 Pro", "pricing": {"input": "$30.00", "output": "$180.00", "cached_read": "$30.00", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K+", "good_for": "highest quality at premium cost", "modalities": ["text", "images", "audio"]},
    "gpt-5.4": {"display_name": "GPT 5.4", "pricing": {"input": "$2.50 (<=272K) / $5.00 (>272K)", "output": "$15.00 (<=272K) / $22.50 (>272K)", "cached_read": "$0.25 (<=272K) / $0.50 (>272K)", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K+", "good_for": "strong general-purpose coding", "modalities": ["text", "images", "audio"]},
    "gpt-5.4-pro": {"display_name": "GPT 5.4 Pro", "pricing": {"input": "$30.00", "output": "$180.00", "cached_read": "$30.00", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K+", "good_for": "premium high-accuracy tasks", "modalities": ["text", "images", "audio"]},
    "gpt-5.4-mini": {"display_name": "GPT 5.4 Mini", "pricing": {"input": "$0.75", "output": "$4.50", "cached_read": "$0.075", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "partial", "context_window": "272K", "good_for": "fast lower-cost production tasks", "modalities": ["text", "images"]},
    "gpt-5.4-nano": {"display_name": "GPT 5.4 Nano", "pricing": {"input": "$0.20", "output": "$1.25", "cached_read": "$0.02", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "partial", "context_window": "272K", "good_for": "ultra-cheap automation", "modalities": ["text"]},
    "gpt-5.3-codex-spark": {"display_name": "GPT 5.3 Codex Spark", "pricing": {"input": "$1.75", "output": "$14.00", "cached_read": "$0.175", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "coding with faster latency", "modalities": ["text"]},
    "gpt-5.3-codex": {"display_name": "GPT 5.3 Codex", "pricing": {"input": "$1.75", "output": "$14.00", "cached_read": "$0.175", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "code generation and edits", "modalities": ["text"]},
    "gpt-5.2": {"display_name": "GPT 5.2", "pricing": {"input": "$1.75", "output": "$14.00", "cached_read": "$0.175", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "stable coding and analysis", "modalities": ["text", "images"]},
    "gpt-5.2-codex": {"display_name": "GPT 5.2 Codex", "pricing": {"input": "$1.75", "output": "$14.00", "cached_read": "$0.175", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "coding-focused variant", "modalities": ["text"]},
    "gpt-5.1": {"display_name": "GPT 5.1", "pricing": {"input": "$1.07", "output": "$8.50", "cached_read": "$0.107", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "cost-effective high quality", "modalities": ["text", "images"]},
    "gpt-5.1-codex": {"display_name": "GPT 5.1 Codex", "pricing": {"input": "$1.07", "output": "$8.50", "cached_read": "$0.107", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "coding-optimized model", "modalities": ["text"]},
    "gpt-5.1-codex-max": {"display_name": "GPT 5.1 Codex Max", "pricing": {"input": "$1.25", "output": "$10.00", "cached_read": "$0.125", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "strongest 5.1 coding variant", "modalities": ["text"]},
    "gpt-5.1-codex-mini": {"display_name": "GPT 5.1 Codex Mini", "pricing": {"input": "$0.25", "output": "$2.00", "cached_read": "$0.025", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "partial", "context_window": "272K", "good_for": "low-cost code tasks", "modalities": ["text"]},
    "gpt-5": {"display_name": "GPT 5", "pricing": {"input": "$1.07", "output": "$8.50", "cached_read": "$0.107", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "general premium reasoning", "modalities": ["text", "images"]},
    "gpt-5-codex": {"display_name": "GPT 5 Codex", "pricing": {"input": "$1.07", "output": "$8.50", "cached_read": "$0.107", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "yes", "context_window": "272K", "good_for": "GPT 5 coding tasks", "modalities": ["text"]},
    "gpt-5-nano": {"display_name": "GPT 5 Nano", "pricing": {"input": "$0.05", "output": "$0.40", "cached_read": "$0.005", "cached_write": "-"}, "endpoint": "/responses", "reasoning": "partial", "context_window": "272K", "good_for": "very cheap automation", "modalities": ["text"]},
}


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _normalize_provider(name: str | None) -> str:
    raw = (name or "").strip().lower()
    return _PROVIDER_ALIASES.get(raw, "openai")


def get_llm_settings(model_override: str | None = None) -> dict[str, str]:
    cfg = _load_config()

    provider = _normalize_provider(
        os.getenv("JARVIS_LLM_PROVIDER")
        or cfg.get("llm_provider")
        or "openai"
    )

    model = (
        (model_override or "").strip()
        or (os.getenv("JARVIS_LLM_MODEL") or "").strip()
        or (cfg.get("llm_model") or "").strip()
        or _DEFAULT_MODELS[provider]
    )

    env_key_name = _ENV_KEY_NAMES[provider]
    cfg_key_name = _CONFIG_KEY_NAMES[provider]
    api_key = (os.getenv(env_key_name) or "").strip() or (cfg.get(cfg_key_name) or "").strip()

    env_url_name = _ENV_BASE_URL_NAMES[provider]
    cfg_url_name = _CONFIG_BASE_URL_NAMES[provider]
    base_url = (
        (os.getenv(env_url_name) or "").strip()
        or (cfg.get(cfg_url_name) or "").strip()
        or _DEFAULT_BASE_URLS[provider]
    )

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    }


def _infer_model_meta(model_id: str, provider: str) -> dict[str, Any]:
    return _finalize_model_meta({"id": model_id}, provider)


def _build_models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def _enrich_zen_metadata(model_id: str) -> dict[str, Any]:
    meta = dict(_ZEN_MODEL_METADATA.get(model_id, {}))
    if not meta:
        meta = {
            "display_name": model_id,
            "pricing": {"input": "unknown", "output": "unknown", "cached_read": "unknown", "cached_write": "unknown"},
            "endpoint": "unknown",
            "reasoning": "unknown",
            "context_window": "unknown",
            "good_for": "general tasks",
            "modalities": ["text"],
        }
    meta["id"] = model_id
    meta["provider"] = "opencode_zen"
    return _finalize_model_meta(meta, "opencode_zen")


def list_models(
    *,
    provider: str,
    api_key: str = "",
    base_url: str = "",
    timeout: int = 20,
) -> list[dict[str, Any]]:
    provider = _normalize_provider(provider)
    key = api_key.strip()
    url = (base_url or _DEFAULT_BASE_URLS[provider]).strip()

    if key and url:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            resp = requests.get(_build_models_url(url), headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data") if isinstance(data, dict) else None
            if isinstance(items, list) and items:
                models: list[dict[str, Any]] = []
                for item in items:
                    if isinstance(item, dict):
                        model_id = str(item.get("id") or "").strip()
                    else:
                        model_id = str(item).strip()
                    if not model_id:
                        continue
                    if provider == "opencode_zen":
                        models.append(_enrich_zen_metadata(model_id))
                    else:
                        models.append(_finalize_model_meta(_infer_model_meta(model_id, provider), provider, url))
                if models:
                    models.sort(key=lambda x: str(x.get("display_name") or x.get("id") or "").lower())
                    return models
        except Exception:
            pass

    fallback = _MODEL_FALLBACKS.get(provider, [])
    return [_finalize_model_meta(dict(x), provider, url) for x in fallback]


def model_tooltip(meta: dict[str, Any]) -> str:
    model_id = str(meta.get("id", "unknown"))
    name = str(meta.get("display_name") or model_id)
    ctx = meta.get("context_window", "unknown")
    reasoning = str(meta.get("reasoning", "unknown"))
    good_for = str(meta.get("good_for", "general tasks"))
    modalities = meta.get("modalities", ["text"])
    if isinstance(modalities, list):
        mod_txt = ", ".join(str(m) for m in modalities)
    else:
        mod_txt = str(modalities)

    endpoint = str(meta.get("endpoint", "unknown"))
    pricing = meta.get("pricing", {})
    if isinstance(pricing, dict):
        in_cost = str(pricing.get("input", "unknown"))
        out_cost = str(pricing.get("output", "unknown"))
        cr_cost = str(pricing.get("cached_read", "unknown"))
        cw_cost = str(pricing.get("cached_write", "unknown"))
    else:
        in_cost = out_cost = cr_cost = cw_cost = "unknown"

    status = "FREE" if _is_free_model(meta, str(meta.get("provider") or ""), str(meta.get("base_url") or "")) else str(meta.get("status", ""))
    status_line = f"Status: {status}\n" if status else ""

    return (
        f"{name}\n"
        f"ID: {model_id}\n"
        f"{status_line}"
        f"Context window: {ctx}\n"
        f"Reasoning: {reasoning}\n"
        f"Best for: {good_for}\n"
        f"Modalities: {mod_txt}\n"
        f"Endpoint: {endpoint}\n"
        f"Price /1M tok - in: {in_cost}, out: {out_cost}\n"
        f"Cache - read: {cr_cost}, write: {cw_cost}"
    )


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts).strip()
    return str(content or "").strip()


def chat_completion(
    *,
    user_prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    temperature: float = 0.2,
    timeout: int = 30,
    max_retries: int = 2,
) -> str:
    settings = get_llm_settings(model_override=model)
    provider = settings["provider"]
    model_name = settings["model"]
    api_key = settings["api_key"]
    base_url = settings["base_url"]

    if not api_key:
        raise RuntimeError(
            f"Missing API key for provider '{provider}'. "
            f"Set it in config/api_keys.json or environment variable {_ENV_KEY_NAMES[provider]}."
        )
    if not base_url:
        raise RuntimeError(
            f"Missing base URL for provider '{provider}'. "
            f"Set {_ENV_BASE_URL_NAMES[provider]} or {_CONFIG_BASE_URL_NAMES[provider]}."
        )

    url = f"{base_url.rstrip('/')}/chat/completions"

    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_err = None
    for attempt in range(max_retries + 1):
        with _llm_lock:
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                try:
                    response.raise_for_status()
                except requests.HTTPError as exc:
                    if response.status_code == 429 and attempt < max_retries:
                        wait = 2 ** attempt
                        print(f"[LLM] Rate limited, retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                    body = response.text[:500].replace("\n", " ")
                    raise RuntimeError(f"LLM API error ({response.status_code}): {body}") from exc

                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError("LLM API returned no choices.")

                message = choices[0].get("message") or {}
                text = _extract_text(message.get("content", ""))
                if not text:
                    raise RuntimeError("LLM API returned empty content.")
                return text
            except requests.exceptions.Timeout:
                last_err = "Request timed out"
                if attempt < max_retries:
                    print(f"[LLM] Timeout, retrying...")
                    continue
            except requests.exceptions.ConnectionError as e:
                last_err = str(e)
                if attempt < max_retries:
                    print(f"[LLM] Connection error, retrying...")
                    time.sleep(1)
                    continue
            except RuntimeError:
                raise

    raise RuntimeError(f"LLM request failed after {max_retries + 1} attempts: {last_err}")
