import json
import os
from typing import List


def validate_jsonl(path: str) -> dict:
    """Validate a JSONL of interactions/exports. Returns a report."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    problems = []
    count = 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            count += 1
            try:
                obj = json.loads(line)
            except Exception as e:
                problems.append({"line": i, "error": "invalid_json", "msg": str(e)})
                continue
            # required fields for training exports
            for fld in ("instruction", "input", "output"):
                if fld not in obj:
                    problems.append({"line": i, "error": "missing_field", "field": fld})
    return {"count": count, "problems": problems}


def get_validation_report(path: str) -> dict:
    return validate_jsonl(path)


def create_correction_pairs(source_jsonl: str, out_jsonl: str, require_correction: bool = True) -> int:
    """Reads a JSONL with 'output' and 'correction' fields and writes instruction->correction pairs."""
    if not os.path.exists(source_jsonl):
        raise FileNotFoundError(source_jsonl)
    written = 0
    with open(source_jsonl, encoding="utf-8") as src, open(out_jsonl, "w", encoding="utf-8") as dst:
        for line in src:
            obj = json.loads(line)
            corr = obj.get("correction")
            if require_correction and not corr:
                continue
            pair = {"instruction": obj.get("instruction") or obj.get("input"), "input": obj.get("input"), "output": corr or obj.get("output")}
            dst.write(json.dumps(pair) + "\n")
            written += 1
    return written
