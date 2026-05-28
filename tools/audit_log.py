#!/usr/bin/env python3
"""Append-only audit log for JARVIS.

Structured JSONL records live beside the repo and can be tailed or replayed
offline. This complements the SQLite audit tables with an immutable file trail.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "audit.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_entry(event_type: str, detail: str, log_path: Path = DEFAULT_LOG_PATH, **metadata: Any) -> Path:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": now_iso(),
        "event_type": event_type,
        "detail": detail,
        "metadata": metadata,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return log_path
