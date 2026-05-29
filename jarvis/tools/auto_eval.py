import os
import json
from typing import Dict

BASE = os.path.join(os.path.dirname(__file__), '..', 'auto_eval')


def _ensure_dir():
    os.makedirs(BASE, exist_ok=True)


LABELS = ["excellent", "good", "mediocre", "poor"]


def score_output(output_text: str, expected_contains: str = None) -> Dict:
    """Lightweight heuristic judge. Returns label and details."""
    score = {"label": "mediocre", "reason": "heuristic default"}
    if not output_text or output_text.strip() == "":
        score = {"label": "poor", "reason": "empty output"}
    elif expected_contains and expected_contains in output_text:
        score = {"label": "excellent", "reason": "contains expected text"}
    elif len(output_text) > 200:
        score = {"label": "good", "reason": "sufficient length"}
    else:
        score = {"label": "mediocre", "reason": "short or partial"}
    return score


def human_override(interaction_id: str, label: str, comment: str, by: str = "human"):
    _ensure_dir()
    path = os.path.join(BASE, "overrides.jsonl")
    entry = {"interaction_id": interaction_id, "label": label, "comment": comment, "by": by}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
