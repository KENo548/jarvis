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
        return None

    @classmethod
    def analyze_screen(
        cls, prompt: str = "What do you see on this screen?"
    ) -> VisionResult:
        """Capture screen and analyze with best available provider."""
        provider = cls._get_available_provider()
        if provider is None:
            return VisionResult(
                description="No vision provider available. Configure OpenAI API key or install llava.",
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
