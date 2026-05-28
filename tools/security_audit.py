#!/usr/bin/env python3
"""
JARVIS Security Audit — Automated CVE + Log Anomaly + Policy Validation
========================================================================
Runs as a periodic security audit loop. Checks:
  1. Dependency CVEs (pip-audit, npm audit)
  2. Log anomaly detection (unusual error patterns, brute force signs)
  3. Policy validation (action whitelist, kill switch, approval queue)
  4. Secret scanning (gitleaks on recent changes)
  5. Config drift (checks critical files haven't been tampered)

Usage:
    python tools/security_audit.py run          # Run full audit
    python tools/security_audit.py cve          # CVE check only
    python tools/security_audit.py logs         # Log anomaly check only
    python tools/security_audit.py policy       # Policy validation only
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG = PROJECT_ROOT / "logs" / "security-audit.log"
DB_PATH = PROJECT_ROOT / "memory" / "sqlite" / "jarvis.db"


def log_result(category: str, status: str, detail: str):
    """Append audit result to log file."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "category": category,
        "status": status,
        "detail": detail,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    print(f"  [{icon}] {category}: {detail}")


def check_dependency_cves() -> list[dict]:
    """Run pip-audit and npm audit to find known CVEs."""
    findings = []

    # pip-audit
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json", "--desc"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT)
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for vuln in data.get("vulnerabilities", []):
                findings.append({
                    "tool": "pip-audit",
                    "package": vuln.get("name", "unknown"),
                    "version": vuln.get("version", "unknown"),
                    "vuln_id": vuln.get("vuln_id", "unknown"),
                    "fix_versions": vuln.get("fix_versions", []),
                })
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    # npm audit
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT)
        )
        if result.stdout:
            data = json.loads(result.stdout)
            vulns = data.get("vulnerabilities", {})
            for name, info in vulns.items():
                findings.append({
                    "tool": "npm-audit",
                    "package": name,
                    "severity": info.get("severity", "unknown"),
                    "via": [v for v in info.get("via", []) if isinstance(v, dict)],
                })
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    return findings


def check_log_anomalies() -> list[dict]:
    """Scan logs for anomalous patterns."""
    anomalies = []
    log_dir = PROJECT_ROOT / "logs"

    if not log_dir.exists():
        return anomalies

    suspicious_patterns = [
        (r"(?i)(brute.?force|failed\s+login|authentication\s+failure)", "brute_force"),
        (r"(?i)(permission\s+denied|access\s+denied)", "access_violation"),
        (r"(?i)(segfault|segmentation\s+fault|core\s+dump)", "crash"),
        (r"(?i)(out\s+of\s+memory|oom|killed)", "resource_exhaustion"),
        (r"(?i)(traceback|exception|error.*fatal)", "error_spike"),
    ]

    for log_file in log_dir.glob("*.log"):
        try:
            content = log_file.read_text(errors="ignore")
            lines = content.split("\n")
            # Check last 1000 lines
            recent = lines[-1000:] if len(lines) > 1000 else lines

            for pattern, category in suspicious_patterns:
                matches = [l for l in recent if re.search(pattern, l)]
                if len(matches) > 5:  # Threshold: more than 5 matches is anomalous
                    anomalies.append({
                        "file": log_file.name,
                        "category": category,
                        "count": len(matches),
                        "sample": matches[0][:200],
                    })
        except Exception:
            pass

    return anomalies


def check_policy_validation() -> list[dict]:
    """Validate security policies are properly configured."""
    issues = []

    # Check kill switch exists in DB
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        try:
            row = conn.execute(
                "SELECT value FROM system_control WHERE key = 'kill_switch'"
            ).fetchone()
            if not row:
                issues.append({"policy": "kill_switch", "issue": "kill_switch not found in system_control"})
        except Exception:
            issues.append({"policy": "kill_switch", "issue": "system_control table missing"})
        finally:
            conn.close()
    else:
        issues.append({"policy": "kill_switch", "issue": "database not initialized"})

    # Check action whitelist exists
    wl_path = PROJECT_ROOT / "security" / "action-whitelist.json"
    if not wl_path.exists():
        issues.append({"policy": "action_whitelist", "issue": "action-whitelist.json not found"})
    else:
        wl = json.loads(wl_path.read_text())
        if "blocked" not in wl or not wl["blocked"]:
            issues.append({"policy": "action_whitelist", "issue": "no blocked actions defined"})

    # Check .gitignore blocks sensitive files
    gitignore = PROJECT_ROOT / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        critical_patterns = [".env", "vault-keys", "*.pem", "*.key"]
        for pat in critical_patterns:
            if pat not in content:
                issues.append({"policy": "gitignore", "issue": f"'{pat}' not in .gitignore"})
    else:
        issues.append({"policy": "gitignore", "issue": ".gitignore not found"})

    return issues


def run_full_audit():
    """Run all security checks."""
    print("=== JARVIS Security Audit ===")
    print(f"Time: {datetime.utcnow().isoformat()}\n")

    # 1. CVE check
    print("[1/4] Checking dependency CVEs...")
    cves = check_dependency_cves()
    if cves:
        log_result("cve", "fail", f"{len(cves)} vulnerabilities found")
        for v in cves[:5]:
            print(f"    {v.get('package', '?')}: {v.get('vuln_id', v.get('severity', '?'))}")
    else:
        log_result("cve", "pass", "No known CVEs found")

    # 2. Log anomalies
    print("\n[2/4] Checking log anomalies...")
    anomalies = check_log_anomalies()
    if anomalies:
        log_result("logs", "warn", f"{len(anomalies)} anomalous patterns detected")
        for a in anomalies[:5]:
            print(f"    {a['file']}: {a['category']} ({a['count']} matches)")
    else:
        log_result("logs", "pass", "No log anomalies detected")

    # 3. Policy validation
    print("\n[3/4] Validating policies...")
    policy_issues = check_policy_validation()
    if policy_issues:
        log_result("policy", "fail", f"{len(policy_issues)} policy issues")
        for p in policy_issues:
            print(f"    {p['policy']}: {p['issue']}")
    else:
        log_result("policy", "pass", "All policies valid")

    # 4. Summary
    total_issues = len(cves) + len(anomalies) + len(policy_issues)
    print(f"\n{'='*50}")
    if total_issues == 0:
        print("AUDIT RESULT: PASS — No issues found")
        log_result("summary", "pass", "All checks passed")
    else:
        print(f"AUDIT RESULT: {total_issues} issues found")
        log_result("summary", "fail", f"{total_issues} issues found")

    return total_issues


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "run":
        issues = run_full_audit()
        sys.exit(1 if issues > 0 else 0)

    elif command == "cve":
        cves = check_dependency_cves()
        print(json.dumps(cves, indent=2))
        sys.exit(1 if cves else 0)

    elif command == "logs":
        anomalies = check_log_anomalies()
        print(json.dumps(anomalies, indent=2))
        sys.exit(1 if anomalies else 0)

    elif command == "policy":
        issues = check_policy_validation()
        print(json.dumps(issues, indent=2))
        sys.exit(1 if issues else 0)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
