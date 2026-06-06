"""Voice testing session report generator.

Post-session analysis tool for the VOICE_TESTING_PROTOCOL.md sessions.
Queries the interaction_logger database and produces structured reports.

Usage:
    python -m tests.voice_session_report                    # Latest session
    python -m tests.voice_session_report --session SID      # Specific session
    python -m tests.voice_session_report --csv              # CSV export
    python -m tests.voice_session_report --summary          # One-line summary
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DB = Path(r"C:\jarvis\memory\sqlite\interactions.db")
THRESHOLD_PASS = 0.45


def get_sessions(limit: int = 10) -> list[dict]:
    """List recent sessions with basic stats."""
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT session_id,
                  COUNT(*) as total,
                  ROUND(AVG(success_score), 3) as avg_score,
                  ROUND(AVG(latency_ms), 0) as avg_latency,
                  MIN(created_at) as first_seen,
                  MAX(created_at) as last_seen
           FROM interactions
           GROUP BY session_id
           ORDER BY MAX(created_at) DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_report(session_id: str | None = None) -> dict:
    """Generate full report for a session."""
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    if session_id:
        rows = conn.execute(
            "SELECT * FROM interactions WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    else:
        session = conn.execute(
            "SELECT session_id FROM interactions ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not session:
            conn.close()
            return {"error": "No sessions found"}
        session_id = session["session_id"]
        rows = conn.execute(
            "SELECT * FROM interactions WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()

    if not rows:
        conn.close()
        return {"session_id": session_id, "total": 0, "passed": 0, "domains": {}}

    by_domain = defaultdict(list)
    for r in rows:
        domain = r["domain"] or "unknown"
        by_domain[domain].append(dict(r))

    total = len(rows)
    passed = sum(1 for r in rows if r["success_score"] and r["success_score"] >= THRESHOLD_PASS)
    failed = total - passed

    results = {
        "session_id": session_id,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "avg_latency_ms": round(sum(r["latency_ms"] or 0 for r in rows) / total, 0) if total else 0,
        "avg_score": round(sum(r["success_score"] or 0 for r in rows) / total, 3) if total else 0,
        "domains": {},
        "failed_commands": [],
    }

    for domain, cmds in sorted(by_domain.items()):
        scores = [c["success_score"] or 0 for c in cmds]
        latencies = [c["latency_ms"] or 0 for c in cmds]
        d_passed = sum(1 for s in scores if s >= THRESHOLD_PASS)
        results["domains"][domain] = {
            "count": len(cmds),
            "passed": d_passed,
            "failed": len(cmds) - d_passed,
            "avg_score": round(sum(scores) / len(scores), 3),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 0),
            "max_latency_ms": round(max(latencies), 0),
        }

    # Collect individual failures
    for r in rows:
        score = r["success_score"] or 0
        if score < THRESHOLD_PASS:
            results["failed_commands"].append(
                {
                    "input_text": (r["input_text"] or "")[:80],
                    "output_text": (r["output_text"] or "")[:120],
                    "latency_ms": r["latency_ms"],
                    "score": score,
                    "agent": r["agent_name"],
                    "domain": r["domain"],
                }
            )

    # Auto-eval distribution
    eval_counts: dict[str, int] = {"excellent": 0, "good": 0, "mediocre": 0, "poor": 0}
    for r in rows:
        s = r["success_score"] or 0
        if s >= 0.85:
            eval_counts["excellent"] += 1
        elif s >= 0.65:
            eval_counts["good"] += 1
        elif s >= 0.45:
            eval_counts["mediocre"] += 1
        else:
            eval_counts["poor"] += 1
    results["quality_distribution"] = eval_counts

    conn.close()
    return results


def print_report(report: dict) -> None:
    """Pretty-print a session report."""
    if "error" in report:
        print(f"Error: {report['error']}")
        return

    print(f"\n{'='*60}")
    print(f"  SAGE Voice Testing Session Report")
    print(f"{'='*60}")
    print(f"  Session:     {report['session_id'][:16]}...")
    print(f"  Commands:    {report['total']}")
    print(f"  Passed:      {report['passed']} ({report['pass_rate']}%)")
    print(f"  Failed:      {report['failed']}")
    print(f"  Avg Latency: {report['avg_latency_ms']}ms")
    print(f"  Avg Score:   {report['avg_score']}")
    print(f"{'='*60}")

    print(f"\n  ┌{'─'*40}┬──────┬────────┬──────────┐")
    print(f"  │ {'Domain':38s} │ Runs │ Passed │ Avg(ms)  │")
    print(f"  ├{'─'*40}┼──────┼────────┼──────────┤")
    for domain, d in report["domains"].items():
        name = domain[:38]
        passed_str = f"{d['passed']}/{d['count']}"
        print(f"  │ {name:38s} │ {d['count']:4d} │ {passed_str:6s} │ {d['avg_latency_ms']:6d}ms │")
    print(f"  └{'─'*40}┴──────┴────────┴──────────┘")

    print(f"\n  Quality Distribution:")
    for label, count in report["quality_distribution"].items():
        bar = "█" * count + "░" * (max(0, 10 - count))
        print(f"    {label:10s} {count:2d}  {bar}")

    if report["failed_commands"]:
        print(f"\n  ❌ Failed Commands ({len(report['failed_commands'])}):")
        for fc in report["failed_commands"]:
            print(f"    • [{fc['domain']}] \"{fc['input_text']}\"")
            print(f"      Score: {fc['score']}  Latency: {fc['latency_ms']}ms")
            print(f"      Output: {fc['output_text']}")
            print()

    print(f"{'='*60}\n")


def export_csv(report: dict) -> str:
    """Export report as CSV."""
    lines = ["session_id,domain,count,passed,failed,avg_score,avg_latency_ms"]
    for domain, d in report.get("domains", {}).items():
        lines.append(
            f"{report['session_id']},{domain},{d['count']},{d['passed']},"
            f"{d['failed']},{d['avg_score']},{d['avg_latency_ms']}"
        )
    return "\n".join(lines)


def summary_line(report: dict) -> str:
    """One-line summary suitable for commit messages or dashboards."""
    if "error" in report:
        return f"SESSION ERROR: {report['error']}"
    return (
        f"VoiceTest session={report['session_id'][:8]} "
        f"pass={report['passed']}/{report['total']} "
        f"rate={report['pass_rate']}% "
        f"latency={report['avg_latency_ms']}ms "
        f"score={report['avg_score']}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice testing session report")
    parser.add_argument("--session", type=str, help="Session ID (default: latest)")
    parser.add_argument("--csv", action="store_true", help="Export as CSV")
    parser.add_argument("--summary", action="store_true", help="One-line summary")
    parser.add_argument("--list", type=int, nargs="?", const=10, help="List recent sessions")
    args = parser.parse_args()

    if args.list:
        sessions = get_sessions(args.list)
        if not sessions:
            print("No sessions found.")
        else:
            print(f"\n  Recent {len(sessions)} sessions:")
            print(f"  {'Session ID':20s} {'Cmds':5s} {'Score':7s} {'Latency':8s} {'First Seen'}")
            print(f"  {'-'*20} {'-'*5} {'-'*7} {'-'*8} {'-'*20}")
            for s in sessions:
                sid = s["session_id"][:16]
                print(
                    f"  {sid:20s} {s['total']:5d} {s['avg_score']:7.3f} {s['avg_latency']:6.0f}ms  {s['last_seen'][:19]}"
                )
        sys.exit(0)

    report = generate_report(args.session)
    if args.csv:
        print(export_csv(report))
    elif args.summary:
        print(summary_line(report))
    else:
        print_report(report)
