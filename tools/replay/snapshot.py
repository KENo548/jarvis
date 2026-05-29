"""Replayable snapshot format for SAGE agent interactions.

Captures the full state of an agent interaction so it can be replayed
identically (modulo non-determinism in the model).
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SNAPSHOT_DIR = Path(r"C:\jarvis\memory\snapshots")


def _env_info() -> dict[str, Any]:
    """Capture environment details for reproducibility."""
    info: dict[str, Any] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }

    # Ollama version
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        info["ollama_version"] = result.stdout.strip()
    except Exception:
        info["ollama_version"] = "unknown"

    # Docker status
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=5,
        )
        info["docker_version"] = result.stdout.strip() if result.returncode == 0 else "not running"
    except Exception:
        info["docker_version"] = "not available"

    # Hash of key tool files for versioning
    tool_files = [
        r"C:\jarvis\tools\llm_client.py",
        r"C:\jarvis\tools\observability\interaction_logger.py",
        r"C:\jarvis\tools\observability\auto_eval.py",
    ]
    tool_hashes: dict[str, str] = {}
    for fp in tool_files:
        p = Path(fp)
        if p.exists():
            h = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
            tool_hashes[p.name] = h
    info["tool_versions"] = tool_hashes

    return info


def create_snapshot(
    task_text: str,
    agent_name: str,
    model: str,
    prompt_version: int | None = None,
    memory_state: dict[str, Any] | None = None,
    tool_versions: dict[str, str] | None = None,
    env_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture full interaction state as a snapshot."""
    snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "snapshot_id": snapshot_id,
        "timestamp": now,
        "task_text": task_text,
        "agent_name": agent_name,
        "model": model,
        "prompt_version": prompt_version,
        "memory_state": memory_state or {},
        "tool_versions": tool_versions or {},
        "env_info": env_info or _env_info(),
    }

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / f"{snapshot_id}.json"
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return snapshot


def load_snapshot(snapshot_id: str) -> dict[str, Any] | None:
    """Load a saved snapshot by ID."""
    p = SNAPSHOT_DIR / f"{snapshot_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def replay_from_snapshot(
    snapshot_id: str,
    model: str | None = None,
) -> dict[str, Any] | None:
    """Replay a snapshot — returns the captured state ready for execution.

    This does NOT automatically invoke the LLM; it returns the reconstructed
    context so the caller can feed it into their agent pipeline.
    """
    snap = load_snapshot(snapshot_id)
    if snap is None:
        return None

    return {
        "snapshot_id": snap["snapshot_id"],
        "replayed_at": datetime.now(timezone.utc).isoformat(),
        "original_timestamp": snap["timestamp"],
        "task_text": snap["task_text"],
        "agent_name": snap["agent_name"],
        "model": model or snap["model"],
        "prompt_version": snap["prompt_version"],
        "memory_state": snap["memory_state"],
        "tool_versions": snap["tool_versions"],
        "env_info": snap["env_info"],
        "status": "ready_to_execute",
    }
