"""Export training data from logged interactions for the SAGE AI ecosystem."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .interaction_logger import _connect

OUTPUT_DIR = Path(r"C:\jarvis\memory\training_data")

QUALITY_LEVELS = {"bad": 0, "mediocre": 0.5, "good": 0.7}


def export_training_data(
    output_path: Optional[str | Path] = None,
    min_quality: str = "good",
    domain: str | None = None,
    has_correction: bool = False,
    format: str = "jsonl",
    db_path: Optional[str | Path] = None,
) -> Path:
    """Export training data from interactions matching the filters.

    Args:
        output_path: Where to write the output file. Auto-generated if None.
        min_quality: Minimum quality threshold ('bad', 'mediocre', 'good').
        domain: Filter by domain (None = all domains).
        has_correction: If True, only export interactions that have corrections.
        format: Output format, only 'jsonl' supported currently.

    Returns:
        Path to the exported file.
    """
    threshold = QUALITY_LEVELS.get(min_quality, 0.7)

    conn = _connect(db_path)
    try:
        clauses: list[str] = ["success_score >= ?"]
        params: list[Any] = [threshold]

        if domain:
            clauses.append("domain = ?")
            params.append(domain)

        if has_correction:
            clauses.append("correction IS NOT NULL AND correction != ''")

        where = " WHERE " + " AND ".join(clauses)
        sql = f"SELECT * FROM interactions{where} ORDER BY created_at ASC"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    records: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        quality_label = _score_to_label(r.get("success_score", 0.0))
        record = {
            "instruction": r.get("input_text", ""),
            "input": r.get("assembled_context", ""),
            "output": r.get("output_text", ""),
            "correction": r.get("correction", ""),
            "domain": r.get("domain", "general"),
            "agent": r.get("agent_name", ""),
            "quality": quality_label,
            "metadata": {
                "interaction_id": r.get("interaction_id", ""),
                "model": r.get("model_name", ""),
                "latency_ms": r.get("latency_ms", 0),
                "timestamp": r.get("timestamp", ""),
            },
        }
        records.append(record)

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"training_data_{ts}.jsonl"

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return out


def export_by_domain(output_dir: Optional[str | Path] = None) -> dict[str, Path]:
    """Split training data into separate files by domain.

    Returns a mapping of domain -> file path.
    """
    base = Path(output_dir) if output_dir else OUTPUT_DIR
    base.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    try:
        domains = conn.execute(
            "SELECT DISTINCT domain FROM interactions"
        ).fetchall()
    finally:
        conn.close()

    result: dict[str, Path] = {}
    for d in domains:
        domain_name = d["domain"]
        out_file = base / f"{domain_name}.jsonl"
        export_training_data(
            output_path=out_file,
            domain=domain_name,
        )
        result[domain_name] = out_file

    return result


def get_export_stats(db_path: Optional[str | Path] = None) -> dict[str, Any]:
    """Return counts of available records by domain and quality level."""
    conn = _connect(db_path)
    try:
        by_domain = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT domain, COUNT(*) FROM interactions GROUP BY domain"
            ).fetchall()
        }

        quality_counts: dict[str, int] = {"bad": 0, "mediocre": 0, "good": 0}
        rows = conn.execute("SELECT success_score FROM interactions").fetchall()
        for row in rows:
            score = row[0] or 0.0
            if score >= 0.7:
                quality_counts["good"] += 1
            elif score >= 0.3:
                quality_counts["mediocre"] += 1
            else:
                quality_counts["bad"] += 1

        total = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        with_correction = conn.execute(
            "SELECT COUNT(*) FROM interactions WHERE correction IS NOT NULL AND correction != ''"
        ).fetchone()[0]

        return {
            "total_records": total,
            "by_domain": by_domain,
            "by_quality": quality_counts,
            "with_correction": with_correction,
        }
    finally:
        conn.close()


def _score_to_label(score: float) -> str:
    """Convert a numeric score to a quality label."""
    if score >= 0.7:
        return "good"
    elif score >= 0.3:
        return "mediocre"
    return "bad"


# ---------------------------------------------------------------------------
# JSONL validation
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"instruction", "input", "output", "domain", "agent"}


def validate_jsonl(file_path: str | Path) -> list[dict[str, Any]]:
    """Validate every line in a JSONL file. Returns list of error dicts."""
    errors: list[dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append({"line": line_num, "error": f"Invalid JSON: {e}"})
                continue
            missing = REQUIRED_FIELDS - set(record.keys())
            if missing:
                errors.append({"line": line_num, "error": f"Missing fields: {sorted(missing)}"})
    return errors


def get_validation_report(file_path: str | Path) -> dict[str, Any]:
    """Return full validation report for a JSONL file."""
    total = 0
    valid = 0
    invalid = 0
    missing_field_counts: dict[str, int] = {}
    domain_dist: dict[str, int] = {}

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            missing = REQUIRED_FIELDS - set(record.keys())
            if missing:
                invalid += 1
                for field in missing:
                    missing_field_counts[field] = missing_field_counts.get(field, 0) + 1
            else:
                valid += 1
                domain = record.get("domain", "unknown")
                domain_dist[domain] = domain_dist.get(domain, 0) + 1

    return {
        "total_lines": total,
        "valid": valid,
        "invalid": invalid,
        "missing_fields": missing_field_counts,
        "domain_distribution": domain_dist,
    }


def create_correction_pairs(
    file_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Filter raw export to records with corrections and write clean JSONL."""
    written = 0
    skipped = 0
    with open(file_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            correction = record.get("correction", "")
            if not correction:
                skipped += 1
                continue
            pair = {
                "instruction": record.get("instruction", ""),
                "input": record.get("input", ""),
                "incorrect_output": record.get("output", ""),
                "correction": correction,
                "domain": record.get("domain", ""),
                "agent": record.get("agent", ""),
            }
            fout.write(json.dumps(pair, ensure_ascii=False) + "\n")
            written += 1

    return {"written": written, "skipped": skipped, "output_path": str(output_path)}
