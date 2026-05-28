#!/usr/bin/env python3
"""
JARVIS Output Validator — SQL Syntax Checker + API Dry-Run
===========================================================
Validates agent outputs before they are used:
  - SQL queries: syntax check via sqlite3 EXPLAIN
  - API calls: preview as dry-run (log the request, don't execute)
  - Code: run in sandbox first

Usage:
    python output_validator.py sql "SELECT * FROM users WHERE id = 1"
    python output_validator.py api GET https://api.example.com/data
    python output_validator.py code "print('hello')"
"""

import json
import sqlite3
import sys
from pathlib import Path


def validate_sql(query: str) -> dict:
    """Check SQL syntax using sqlite3 EXPLAIN (read-only, no execution)."""
    query = query.strip().rstrip(";")
    dangerous = ["DROP", "TRUNCATE", "DELETE", "ALTER", "INSERT", "UPDATE"]
    keyword = query.split()[0].upper() if query.split() else ""

    if keyword in dangerous:
        return {
            "valid": False,
            "error": f"Dangerous operation detected: {keyword}",
            "suggestion": "This operation requires approval. Use the approval queue."
        }

    import tempfile
    tmp_path = Path(tempfile.mktemp(suffix=".db"))
    conn = None
    try:
        conn = sqlite3.connect(str(tmp_path))
        conn.execute(f"EXPLAIN {query}")
        conn.close()
        conn = None
        return {"valid": True, "query": query}
    except sqlite3.OperationalError as e:
        return {"valid": False, "error": str(e), "query": query}
    except Exception as e:
        return {"valid": False, "error": str(e), "query": query}
    finally:
        if conn:
            conn.close()
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def validate_api(method: str, url: str, headers: dict = None, body: str = None) -> dict:
    """Preview an API call as a dry-run without executing it."""
    return {
        "dry_run": True,
        "method": method.upper(),
        "url": url,
        "headers": headers or {},
        "body": body,
        "note": "This is a preview. The call was NOT executed. Approve via the approval queue to execute."
    }


def validate_code(code: str) -> dict:
    """Run code in the sandbox and return the result."""
    try:
        from sandbox_runner import run_python_snippet
        result = run_python_snippet(code, timeout_seconds=5)
        return {
            "valid": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500]
        }
    except ImportError:
        return {"valid": False, "error": "sandbox_runner not available"}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "sql":
        query = " ".join(sys.argv[2:])
        result = validate_sql(query)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)

    elif command == "api":
        if len(sys.argv) < 4:
            print("Usage: output_validator.py api <METHOD> <URL>")
            sys.exit(1)
        result = validate_api(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "code":
        code = " ".join(sys.argv[2:])
        result = validate_code(code)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
