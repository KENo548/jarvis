#!/usr/bin/env python3
"""
JARVIS Action Whitelist — Runtime Enforcement
==============================================
Checks agent actions against a whitelist before execution.
Auto-allowed: read files, search web, run tests in sandbox.
Everything else requires approval.

Usage:
    python action_whitelist.py check <agent_id> <action_type> <action_detail>
    python action_whitelist.py list
    python action_whitelist.py add <action_type> [auto_approve]
"""

import json
import sys
from pathlib import Path

WHITELIST_PATH = Path(__file__).resolve().parent.parent / "security" / "action-whitelist.json"

DEFAULT_WHITELIST = {
    "version": "1.0.0",
    "auto_allow": {
        "read": ["read_file", "read_directory", "search_files", "grep"],
        "web": ["web_search", "fetch_url", "browse_page"],
        "test": ["run_tests", "run_pytest", "run_lint"],
        "memory": ["store_memory", "recall_memory", "search_memory"],
        "analysis": ["analyze_code", "review_diff", "check_dependencies"]
    },
    "require_approval": {
        "write": ["write_file", "edit_file", "delete_file"],
        "git": ["git_commit", "git_push", "git_merge", "create_pr"],
        "deploy": ["deploy", "restart_service", "modify_docker"],
        "shell": ["run_shell_command", "install_package"],
        "secrets": ["read_secret", "write_secret", "rotate_key"],
        "database": ["write_query", "schema_change", "backup_database"]
    },
    "blocked": ["drop_table", "delete_repo", "force_push", "disable_firewall"]
}


def load_whitelist() -> dict:
    if WHITELIST_PATH.exists():
        return json.loads(WHITELIST_PATH.read_text())
    return DEFAULT_WHITELIST


def save_whitelist(wl: dict) -> None:
    WHITELIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WHITELIST_PATH.write_text(json.dumps(wl, indent=2))


def check_action(agent_id: str, action_type: str, action_detail: str) -> dict:
    """Check if an action is allowed, requires approval, or is blocked."""
    wl = load_whitelist()

    # Check blocked first
    for blocked in wl.get("blocked", []):
        if blocked.lower() in action_detail.lower():
            return {"status": "blocked", "reason": f"Action matches blocked pattern: {blocked}"}

    # Check auto-allow
    for category, actions in wl.get("auto_allow", {}).items():
        if action_type in actions or action_detail in actions:
            return {"status": "auto_allowed", "category": category}

    # Check require_approval
    for category, actions in wl.get("require_approval", {}).items():
        if action_type in actions or action_detail in actions:
            return {"status": "requires_approval", "category": category}

    # Default: require approval (safe default)
    return {"status": "requires_approval", "category": "unknown_action"}


def list_whitelist() -> None:
    wl = load_whitelist()
    print("=== Auto-Allowed Actions ===")
    for category, actions in wl.get("auto_allow", {}).items():
        print(f"  {category}: {', '.join(actions)}")
    print("\n=== Require Approval ===")
    for category, actions in wl.get("require_approval", {}).items():
        print(f"  {category}: {', '.join(actions)}")
    print(f"\n=== Blocked ===")
    print(f"  {', '.join(wl.get('blocked', []))}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        if len(sys.argv) < 5:
            print("Usage: action_whitelist.py check <agent_id> <action_type> <action_detail>")
            sys.exit(1)
        result = check_action(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] != "blocked" else 1)

    elif command == "list":
        list_whitelist()

    elif command == "add":
        if len(sys.argv) < 4:
            print("Usage: action_whitelist.py add <action_type> [auto_approve]")
            sys.exit(1)
        wl = load_whitelist()
        action = sys.argv[2]
        auto = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
        if auto:
            wl.setdefault("auto_allow", {}).setdefault("custom", []).append(action)
        else:
            wl.setdefault("require_approval", {}).setdefault("custom", []).append(action)
        save_whitelist(wl)
        print(f"Added {action} to {'auto_allow' if auto else 'require_approval'}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
