#!/usr/bin/env python3
"""Vision provider base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VisionResult:
    """Result from a vision analysis."""
    description: str
    text_content: str = ""
    provider: str = ""
    confidence: float = 0.0
    raw_response: str = ""


class VisionProvider(ABC):
    """Base class for vision providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'openai', 'ollama')."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider can be used right now."""

    @abstractmethod
    def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe what you see on this screen.",
        mime_type: str = "image/png",
    ) -> VisionResult:
        """Analyze an image and return a VisionResult."""

    def analyze_screen(
        self,
        prompt: str = "Describe what you see on this screen.",
    ) -> VisionResult:
        """Capture screen and analyze it."""
        screenshot = capture_screen()
        if screenshot is None:
            return VisionResult(
                description="Could not capture screen",
                provider=self.name,
            )
        return self.analyze_image(screenshot, prompt)


def capture_screen() -> bytes | None:
    """Capture the full screen and return PNG bytes."""
    try:
        import mss
        import mss.tools

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # full screen
            img = sct.grab(monitor)
            png = mss.tools.to_png(img.rgb, img.size)
            return png
    except ImportError:
        pass

    try:
        from PIL import ImageGrab
        import io

        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        pass

    return None
