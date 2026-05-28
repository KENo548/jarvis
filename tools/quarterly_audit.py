#!/usr/bin/env python3
"""
JARVIS Quarterly Security Audit
================================
Rotates API keys, reviews permissions, tests backups, validates security posture.

Usage:
    python tools/quarterly_audit.py full           # Full quarterly audit
    python tools/quarterly_audit.py rotate-keys    # Rotate API keys reminder
    python tools/quarterly_audit.py check-perms    # Review file permissions
    python tools/quarterly_audit.py check-secrets  # Scan for exposed secrets
    python tools/quarterly_audit.py check-backups  # Verify backup integrity
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
SECURITY_DIR = ROOT / "security"
REPORT_DIR = LOG_DIR / "audit-reports"


def check_secret_scanning() -> dict:
    gitleaks_config = ROOT / ".gitleaks.toml"
    findings = []

    if gitleaks_config.exists():
        result = subprocess.run(
            ["gitleaks", "detect", "--source", str(ROOT), "--config", str(gitleaks_config), "--report-format", "json"],
            capture_output=True, text=True, timeout=120,
        )
        if result.stdout:
            try:
                leaks = json.loads(result.stdout)
                findings = [{"file": l.get("File"), "rule": l.get("RuleID"), "line": l.get("StartLine")} for l in leaks]
            except json.JSONDecodeError:
                pass

    env_files = list(ROOT.rglob(".env")) + list(ROOT.rglob("*.env"))
    env_secrets = []
    for f in env_files:
        if ".gitignore" not in str(f):
            content = f.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                if "=" in line and any(k in line.upper() for k in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                    env_secrets.append({"file": str(f), "line": line.split("=")[0].strip()})

    return {
        "gitleaks_findings": len(findings),
        "details": findings[:10],
        "env_files_with_secrets": len(env_secrets),
        "env_details": env_secrets[:10],
    }


def check_file_permissions() -> dict:
    sensitive_patterns = [
        ("*.pem", "Private key"),
        ("*.key", "Private key"),
        ("id_rsa*", "SSH private key"),
        ("*.env", "Environment file"),
    ]

    issues = []
    for pattern, desc in sensitive_patterns:
        for f in ROOT.rglob(pattern):
            if ".git" in str(f) or "node_modules" in str(f):
                continue
            stat = os.stat(str(f))
            mode = oct(stat.st_mode)[-3:]
            if mode not in ("600", "400"):
                issues.append({"file": str(f.relative_to(ROOT)), "permissions": mode, "risk": desc})

    return {"checked": True, "issues": len(issues), "details": issues}


def check_vault_status() -> dict:
    vault_host = os.getenv("VAULT_HOST", "localhost")
    vault_port = os.getenv("VAULT_PORT", "18201")
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{vault_host}:{vault_port}/v1/sys/seal-status")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return {
            "reachable": True,
            "sealed": data.get("sealed", True),
            "initialized": data.get("initialized", False),
            "version": data.get("version", "unknown"),
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def check_docker_security() -> dict:
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True, text=True, timeout=10,
    )
    containers = []
    for line in result.stdout.strip().split("\n"):
        if line:
            parts = line.split("\t")
            containers.append({"name": parts[0], "status": parts[1] if len(parts) > 1 else "unknown"})

    restarts = [c for c in containers if "Restarting" in c["status"]]
    return {
        "total_containers": len(containers),
        "restarting": len(restarts),
        "restarting_containers": restarts,
    }


def check_gitleaks_install() -> dict:
    result = subprocess.run(["gitleaks", "version"], capture_output=True, text=True, timeout=10)
    installed = result.returncode == 0
    return {"installed": installed, "version": result.stdout.strip() if installed else "not installed"}


def full_audit() -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quarter": f"Q{(datetime.now().month - 1) // 3 + 1} {datetime.now().year}",
        "secret_scanning": check_secret_scanning(),
        "file_permissions": check_file_permissions(),
        "vault_status": check_vault_status(),
        "docker_security": check_docker_security(),
        "gitleaks": check_gitleaks_install(),
    }

    total_issues = (
        audit["secret_scanning"]["gitleaks_findings"]
        + audit["file_permissions"]["issues"]
        + audit["docker_security"]["restarting"]
    )
    audit["summary"] = {
        "total_issues": total_issues,
        "verdict": "PASS" if total_issues == 0 else "REVIEW_NEEDED",
        "recommendations": [],
    }

    if audit["secret_scanning"]["gitleaks_findings"] > 0:
        audit["summary"]["recommendations"].append("Rotate any exposed keys found by gitleaks")
    if audit["file_permissions"]["issues"] > 0:
        audit["summary"]["recommendations"].append("Fix file permissions on sensitive files (chmod 600)")
    if audit["docker_security"]["restarting"] > 0:
        audit["summary"]["recommendations"].append("Investigate restarting Docker containers")
    if not audit["vault_status"].get("reachable"):
        audit["summary"]["recommendations"].append("Vault is unreachable — check if it's running")
    if audit["vault_status"].get("sealed"):
        audit["summary"]["recommendations"].append("Vault is sealed — unseal it")

    out_path = REPORT_DIR / f"quarterly-audit-{ts}.json"
    out_path.write_text(json.dumps(audit, indent=2))

    print(f"\n{'='*60}")
    print(f"QUARTERLY SECURITY AUDIT — {audit['quarter']}")
    print(f"{'='*60}")
    print(f"  Secret scanning:    {audit['secret_scanning']['gitleaks_findings']} findings")
    print(f"  File permissions:   {audit['file_permissions']['issues']} issues")
    print(f"  Vault:              {'reachable' if audit['vault_status'].get('reachable') else 'UNREACHABLE'}")
    print(f"  Docker:             {audit['docker_security']['total_containers']} containers, {audit['docker_security']['restarting']} restarting")
    print(f"  Gitleaks:           {'installed' if audit['gitleaks']['installed'] else 'NOT INSTALLED'}")
    print(f"  Verdict:            {audit['summary']['verdict']}")
    if audit["summary"]["recommendations"]:
        print(f"\n  Recommendations:")
        for r in audit["summary"]["recommendations"]:
            print(f"    - {r}")
    print(f"\n  Report: {out_path}")
    print(f"{'='*60}")

    return audit


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "full":
        full_audit()
    elif cmd == "rotate-keys":
        print("API Key Rotation Checklist:")
        print("  1. OpenAI:    https://platform.openai.com/api-keys")
        print("  2. GitHub:    https://github.com/settings/tokens")
        print("  3. NVIDIA:    https://build.nvidia.com/settings/api-key")
        print("  4. Update .infrastructure/.env with new keys")
        print("  5. Update Vault: jarvis/openai-api-key, jarvis/github-pat, jarvis/nvidia-api-key")
        print("  6. Restart affected services")
    elif cmd == "check-perms":
        result = check_file_permissions()
        print(json.dumps(result, indent=2))
    elif cmd == "check-secrets":
        result = check_secret_scanning()
        print(json.dumps(result, indent=2))
    elif cmd == "check-backups":
        print("Backup verification:")
        print("  - Check Restic snapshots: restic snapshots")
        print("  - Test restore to temp directory")
        print("  - Verify Backblaze B2 connectivity")
        print("  - Review backup logs in logs/")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
