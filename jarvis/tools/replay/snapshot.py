import os
import json
import datetime

BASE = os.path.join(os.path.dirname(__file__), '..', 'replay')


def _ensure_dir():
    os.makedirs(BASE, exist_ok=True)


def capture_snapshot(session_id: str, workflow_id: str, prompt_version: str, memory_snapshot: dict, tool_versions: dict, orchestration_state: dict = None) -> str:
    _ensure_dir()
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = os.path.join(BASE, f"snapshot-{session_id}-{ts}.json")
    payload = {
        "session_id": session_id,
        "workflow_id": workflow_id,
        "prompt_version": prompt_version,
        "memory_snapshot": memory_snapshot,
        "tool_versions": tool_versions,
        "orchestration_state": orchestration_state or {},
        "timestamp": ts,
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return filename
