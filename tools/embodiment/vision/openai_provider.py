#!/usr/bin/env python3
"""OpenAI GPT-4o vision provider."""

from __future__ import annotations

import base64
import json
import os
import urllib.request
import urllib.error

from .provider import VisionProvider, VisionResult


class OpenAIVisionProvider(VisionProvider):
    """Vision provider using OpenAI GPT-4o."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
                from vault_client import VaultClient
                vc = VaultClient()
                secret = vc.read_secret("jarvis/openai-api-key")
                if secret:
                    self._api_key = secret.value
            except Exception:
                pass

    @property
    def name(self) -> str:
        return "openai/gpt-4o"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe what you see on this screen.",
        mime_type: str = "image/png",
    ) -> VisionResult:
        if not self._api_key:
            return VisionResult(
                description="OpenAI API key not configured",
                provider=self.name,
            )

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
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                text = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                return VisionResult(
                    description=text,
                    provider=self.name,
                    confidence=0.9,
                    raw_response=json.dumps(usage),
                )
        except Exception as e:
            return VisionResult(
                description=f"OpenAI vision error: {e}",
                provider=self.name,
            )
