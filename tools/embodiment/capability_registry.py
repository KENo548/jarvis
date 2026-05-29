#!/usr/bin/env python3
"""SAGE Capability Registry — Tier 1 embodiment tools.

Each capability declares its metadata: risk level, approval requirements,
inputs/outputs, dependencies, and runtime constraints.

Registry = available + tested + executable.
New tools are added ONLY when fully integrated and tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    LOW = "low"        # auto-execute, just log
    MEDIUM = "medium"  # log + notify user
    HIGH = "high"      # explicit approval required


@dataclass
class Capability:
    """Metadata for a single embodied tool."""

    # Identity
    name: str                    # "browser_navigation"
    implementation: str          # "browser_control.py"
    description: str

    # Classification
    domain: str                  # "browser" | "files" | "os" | "vision" | "voice" | "apps"
    risk: RiskLevel

    # Safety
    approval_required: bool
    sandboxable: bool
    rollback_possible: bool
    destructive: bool            # can it delete/overwrite data?

    # Interface
    inputs: list[str]
    outputs: list[str]
    dependencies: list[str]      # other capabilities this needs

    # Runtime
    timeout_seconds: int = 30
    requires_display: bool = False
    requires_internet: bool = False


# ---------------------------------------------------------------------------
# Tier 1 — Registered: available + tested + executable
# ---------------------------------------------------------------------------

CAPABILITIES: dict[str, Capability] = {
    "voice_io": Capability(
        name="voice_io",
        implementation="voice_io.py",
        description="Microphone input + TTS output via Whisper/Edge TTS",
        domain="voice",
        risk=RiskLevel.LOW,
        approval_required=False,
        sandboxable=False,
        rollback_possible=False,
        destructive=False,
        inputs=["text_to_speak", "listen_timeout"],
        outputs=["transcribed_text", "audio_status"],
        dependencies=[],
        requires_display=False,
        requires_internet=False,
    ),
    "app_launcher": Capability(
        name="app_launcher",
        implementation="open_app.py",
        description="Launch any installed application by name",
        domain="apps",
        risk=RiskLevel.LOW,
        approval_required=False,
        sandboxable=False,
        rollback_possible=True,
        destructive=False,
        inputs=["app_name"],
        outputs=["status", "pid"],
        dependencies=[],
        requires_display=True,
        requires_internet=False,
    ),
    "screen_vision": Capability(
        name="screen_vision",
        implementation="vision/",
        description="Capture and understand screen/webcam content via vision LLM",
        domain="vision",
        risk=RiskLevel.LOW,
        approval_required=False,
        sandboxable=False,
        rollback_possible=False,
        destructive=False,
        inputs=["region", "question"],
        outputs=["description", "text_content", "screenshot_path"],
        dependencies=[],
        requires_display=True,
        requires_internet=True,
    ),
    "browser_navigation": Capability(
        name="browser_navigation",
        implementation="browser_control.py",
        description="Control browser — navigate, click, type, scrape via Playwright",
        domain="browser",
        risk=RiskLevel.MEDIUM,
        approval_required=False,
        sandboxable=False,
        rollback_possible=False,
        destructive=False,
        inputs=["url", "action", "selector"],
        outputs=["page_content", "screenshot", "status"],
        dependencies=["screen_vision"],
        requires_display=True,
        requires_internet=True,
    ),
    "file_operations": Capability(
        name="file_operations",
        implementation="file_controller.py",
        description="Read, write, move, delete files with safe path validation",
        domain="files",
        risk=RiskLevel.HIGH,
        approval_required=True,
        sandboxable=True,
        rollback_possible=True,
        destructive=True,
        inputs=["operation", "path", "content"],
        outputs=["result", "status"],
        dependencies=[],
        requires_display=False,
        requires_internet=False,
    ),
    "os_control": Capability(
        name="os_control",
        implementation="computer_control.py",
        description="Mouse, keyboard, hotkeys, screen interaction via PyAutoGUI",
        domain="os",
        risk=RiskLevel.HIGH,
        approval_required=True,
        sandboxable=False,
        rollback_possible=False,
        destructive=True,
        inputs=["action", "target", "value"],
        outputs=["status", "screenshot"],
        dependencies=["screen_vision"],
        requires_display=True,
        requires_internet=False,
    ),
    "system_settings": Capability(
        name="system_settings",
        implementation="computer_settings.py",
        description="Volume, brightness, WiFi, power, dark mode, window management",
        domain="os",
        risk=RiskLevel.LOW,
        approval_required=False,
        sandboxable=False,
        rollback_possible=True,
        destructive=False,
        inputs=["action", "description", "value"],
        outputs=["status"],
        dependencies=[],
        requires_display=True,
        requires_internet=False,
    ),
}


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

def get_capability(name: str) -> Capability | None:
    """Get a registered capability by name."""
    return CAPABILITIES.get(name)


def list_capabilities(domain: str | None = None) -> list[Capability]:
    """List all capabilities, optionally filtered by domain."""
    caps = list(CAPABILITIES.values())
    if domain:
        caps = [c for c in caps if c.domain == domain]
    return caps


def requires_approval(name: str) -> bool:
    """Check if a capability requires approval before execution."""
    cap = get_capability(name)
    return cap.approval_required if cap else True  # unknown = require approval


def get_risk_level(name: str) -> RiskLevel | None:
    """Get the risk level of a capability."""
    cap = get_capability(name)
    return cap.risk if cap else None


def register_capability(capability: Capability) -> None:
    """Register a new capability (for Tier 2+ tools added later)."""
    CAPABILITIES[capability.name] = capability


def get_execution_order() -> list[str]:
    """Return the recommended tool integration order (dependency-aware)."""
    return [
        "voice_io",
        "app_launcher",
        "screen_vision",
        "browser_navigation",
        "file_operations",
        "os_control",
        "system_settings",
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        import json
        from dataclasses import asdict
        out = {k: asdict(v) for k, v in CAPABILITIES.items()}
        # Convert RiskLevel to string for JSON
        for v in out.values():
            v["risk"] = v["risk"]["value"] if isinstance(v["risk"], dict) else v["risk"]
        print(json.dumps(out, indent=2))
    else:
        print(f"SAGE Capability Registry — {len(CAPABILITIES)} Tier 1 tools\n")
        for name in get_execution_order():
            cap = CAPABILITIES[name]
            risk = cap.risk.value.upper()
            approve = " [APPROVAL REQUIRED]" if cap.approval_required else ""
            print(f"  {risk:6s}  {name:25s}  {cap.description[:60]}{approve}")
        print(f"\nTier 2 tools added after integration and testing.")
