#!/usr/bin/env python3
"""SAGE Vision — multi-provider screen analysis.

Usage:
    from vision import Vision
    result = Vision.analyze_screen("What apps are open?")
    result = Vision.analyze_image(png_bytes, "Describe this image")

Provider priority: OpenAI GPT-4o > Ollama llava
"""

from __future__ import annotations

from .provider import VisionProvider, VisionResult, capture_screen
from .openai_provider import OpenAIVisionProvider
from .ollama_provider import OllamaVisionProvider


class Vision:
    """Facade for multi-provider screen vision."""

    _providers: list[VisionProvider] = []

    @classmethod
    def _get_providers(cls) -> list[VisionProvider]:
        if not cls._providers:
            cls._providers = [
                OpenAIVisionProvider(),
                OllamaVisionProvider(),
            ]
        return cls._providers

    @classmethod
    def _get_available_provider(cls) -> VisionProvider | None:
        for p in cls._get_providers():
            if p.is_available:
                return p
        # Fallback: try llm_client to reach Ollama vision models
        try:
            from tools.llm_client import _resolve_provider
            ollama = _resolve_provider("ollama/llama3.2")
            if ollama and "ollama" in ollama.name:
                # Try llama3.2-vision or llava via direct Ollama API
                from .ollama_provider import OllamaVisionProvider
                for vision_model in ["llama3.2-vision:latest", "llava:latest", "llama3.2-vision", "llava"]:
                    fallback = OllamaVisionProvider(model=vision_model)
                    if fallback.is_available:
                        return fallback
        except Exception:
            pass
        return None

    @classmethod
    def analyze_screen(
        cls, prompt: str = "What do you see on this screen?"
    ) -> VisionResult:
        """Capture screen and analyze with best available provider."""
        provider = cls._get_available_provider()
        if provider is None:
            # Ultimate fallback: use llm_client text-only as a best-effort response
            try:
                from tools.llm_client import llm_call
                response = llm_call(
                    prompt=f"[Vision analysis unavailable — no vision model detected]\n\nThe user asked to analyze their screen: '{prompt}'\nPlease explain that vision is not available and suggest installing llama3.2-vision via Ollama.",
                    model="ollama/llama3.2",
                )
                return VisionResult(
                    description=f"[Vision unavailable — text fallback]\n{response.text}",
                    provider="text-fallback",
                )
            except Exception:
                pass
            return VisionResult(
                description="No vision provider available. Configure OpenAI API key or install Ollama with llama3.2-vision / llava.",
                provider="none",
            )
        return provider.analyze_screen(prompt)

    @classmethod
    def analyze_image(
        cls,
        image_data: bytes,
        prompt: str = "Describe this image.",
        mime_type: str = "image/png",
    ) -> VisionResult:
        """Analyze an image with best available provider."""
        provider = cls._get_available_provider()
        if provider is None:
            # Ultimate fallback: use llm_client text-only
            try:
                from tools.llm_client import llm_call
                response = llm_call(
                    prompt=f"[Vision analysis unavailable — no vision model detected]\n\nThe user asked to analyze an image: '{prompt}'\nPlease explain that vision is not available and suggest installing llama3.2-vision via Ollama.",
                    model="ollama/llama3.2",
                )
                return VisionResult(
                    description=f"[Vision unavailable — text fallback]\n{response.text}",
                    provider="text-fallback",
                )
            except Exception:
                pass
            return VisionResult(
                description="No vision provider available.",
                provider="none",
            )
        return provider.analyze_image(image_data, prompt, mime_type)

    @classmethod
    def list_providers(cls) -> list[dict]:
        """List all providers and their status."""
        return [
            {"name": p.name, "available": p.is_available}
            for p in cls._get_providers()
        ]
