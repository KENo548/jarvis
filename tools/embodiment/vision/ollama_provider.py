#!/usr/bin/env python3
"""Ollama vision provider (fallback)."""

from __future__ import annotations

import base64
import json
import urllib.request
import urllib.error

from .provider import VisionProvider, VisionResult


class OllamaVisionProvider(VisionProvider):
    """Vision provider using Ollama (e.g. llava)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llava:latest"):
        self._base_url = base_url
        self._model = model

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    @property
    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                return any(self._model in m for m in models)
        except Exception:
            return False

    def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe what you see on this screen.",
        mime_type: str = "image/png",
    ) -> VisionResult:
        b64 = base64.b64encode(image_data).decode()

        body = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "images": [b64],
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                text = result.get("response", "")
                return VisionResult(
                    description=text,
                    provider=self.name,
                    confidence=0.6,
                )
        except Exception as e:
            return VisionResult(
                description=f"Ollama vision error: {e}",
                provider=self.name,
            )
