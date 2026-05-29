"""Prompt registry — file-based prompt version control for SAGE agents.

Prompts are stored under ``PROMPT_DIR`` as ``<agent>/<version>.txt`` files
with a ``<agent>/meta.json`` metadata sidecar.
"""

from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PROMPT_DIR = Path(r"C:\jarvis\tools\prompt_store\prompts")


def _meta_path(agent_name: str) -> Path:
    return PROMPT_DIR / agent_name / "meta.json"


def _version_path(agent_name: str, version: int) -> Path:
    return PROMPT_DIR / agent_name / f"v{version}.txt"


def _load_meta(agent_name: str) -> dict[str, Any]:
    p = _meta_path(agent_name)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"agent": agent_name, "current_version": 0, "versions": []}


def _save_meta(agent_name: str, meta: dict[str, Any]) -> None:
    p = _meta_path(agent_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def register_prompt(
    agent_name: str,
    prompt_text: str,
    version: int | None = None,
    changelog: str = "",
) -> dict[str, Any]:
    """Save a prompt version. Auto-increments if version is None."""
    meta = _load_meta(agent_name)
    if version is None:
        version = meta["current_version"] + 1

    vp = _version_path(agent_name, version)
    vp.parent.mkdir(parents=True, exist_ok=True)
    vp.write_text(prompt_text, encoding="utf-8")

    entry = {
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changelog": changelog,
        "size_bytes": len(prompt_text.encode("utf-8")),
    }
    meta["versions"].append(entry)
    meta["current_version"] = version
    _save_meta(agent_name, meta)
    return entry


def get_prompt(
    agent_name: str,
    version: int | None = None,
) -> dict[str, Any] | None:
    """Load a prompt. Returns latest version if version is None."""
    meta = _load_meta(agent_name)
    if not meta["versions"]:
        return None

    if version is None:
        version = meta["current_version"]

    vp = _version_path(agent_name, version)
    if not vp.exists():
        return None

    text = vp.read_text(encoding="utf-8")
    entry = next((v for v in meta["versions"] if v["version"] == version), {})
    return {"version": version, "text": text, **entry}


def list_versions(agent_name: str) -> list[dict[str, Any]]:
    """Return all stored versions with timestamps."""
    meta = _load_meta(agent_name)
    return meta["versions"]


def rollback_prompt(agent_name: str, target_version: int) -> dict[str, Any] | None:
    """Revert to a previous version by setting it as current."""
    meta = _load_meta(agent_name)
    vp = _version_path(agent_name, target_version)
    if not vp.exists():
        return None

    meta["current_version"] = target_version
    _save_meta(agent_name, meta)
    return get_prompt(agent_name, target_version)


def diff_prompts(agent_name: str, v1: int, v2: int) -> dict[str, Any]:
    """Show differences between two prompt versions."""
    p1 = _version_path(agent_name, v1)
    p2 = _version_path(agent_name, v2)

    text1 = p1.read_text(encoding="utf-8") if p1.exists() else ""
    text2 = p2.read_text(encoding="utf-8") if p2.exists() else ""

    diff_lines = list(difflib.unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile=f"v{v1}",
        tofile=f"v{v2}",
    ))

    return {
        "v1": v1,
        "v2": v2,
        "diff": "".join(diff_lines),
        "identical": text1 == text2,
    }
