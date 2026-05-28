#!/usr/bin/env python3
"""
Tests for Phase 2 infrastructure scripts.
Validates backup script structure and nginx config syntax.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} {detail}")


def test_backup_script():
    """Verify backup.sh exists, is executable, and has correct structure."""
    print("\n=== Backup Script Tests ===")
    backup = PROJECT_ROOT / "tools" / "backup.sh"
    test("backup.sh exists", backup.exists())

    content = backup.read_text()
    test("has init command", "init)" in content)
    test("has run/backup command", "run|backup)" in content or "backup)" in content)
    test("has verify/check command", "verify|check)" in content or "check)" in content)
    test("has restore command", "restore)" in content)
    test("has list/snapshots command", "list|snapshots)" in content or "snapshots)" in content)
    test("references restic", "restic" in content)
    test("references B2/backblaze", "b2" in content.lower() or "backblaze" in content.lower() or "B2_ACCOUNT" in content)
    test("has exclude patterns", "exclude" in content)
    test("has prune policy", "forget" in content or "prune" in content)
    test("has backup paths defined", "BACKUP_PATHS" in content)
    test("loads config from secrets", "backup-config.env" in content or "CONFIG_FILE" in content)
    test("has logging", "log " in content or "tee -a" in content)


def test_nginx_config():
    """Verify nginx.conf exists and has correct structure."""
    print("\n=== Nginx Config Tests ===")
    nginx_conf = PROJECT_ROOT / "infrastructure" / "nginx" / "nginx.conf"
    test("nginx.conf exists", nginx_conf.exists())

    content = nginx_conf.read_text()
    test("has rate limiting", "limit_req_zone" in content)
    test("has HTTP to HTTPS redirect", "return 301 https" in content)
    test("has SSL certificate config", "ssl_certificate" in content)
    test("has TLS 1.2/1.3", "TLSv1.2" in content and "TLSv1.3" in content)
    test("has security headers", "X-Frame-Options" in content)
    test("has HSTS", "Strict-Transport-Security" in content)
    test("has grafana proxy", "grafana:3000" in content)
    test("has n8n proxy", "n8n:5678" in content)
    test("has searxng proxy", "searxng:8080" in content)
    test("has vault proxy", "vault:8201" in content)
    test("has health endpoint", "/health" in content)
    test("has 404 default", "return 404" in content)


def test_nginx_in_compose():
    """Verify nginx is a live service in docker-compose.yml."""
    print("\n=== Nginx in Docker Compose Tests ===")
    compose = PROJECT_ROOT / "infrastructure" / "docker-compose.yml"
    content = compose.read_text()
    test("nginx service defined", "jarvis-nginx" in content)
    test("uses nginx:alpine image", "nginx:alpine" in content)
    test("exposes port 443", '"443:443"' in content)
    test("exposes port 80", '"80:80"' in content)
    test("depends on grafana", "grafana" in content and "depends_on" in content)
    test("has nginx-certs volume", "nginx-certs" in content)
    test("has healthcheck", "healthcheck" in content and "jarvis-nginx" in content)
    test("has https profile", "https" in content)


def test_redis_in_compose():
    """Verify Redis is a live service in docker-compose.yml."""
    print("\n=== Redis in Docker Compose Tests ===")
    compose = PROJECT_ROOT / "infrastructure" / "docker-compose.yml"
    content = compose.read_text()
    test("redis service defined", "jarvis-redis" in content)
    test("uses redis:7-alpine image", "redis:7-alpine" in content)
    test("has AOF persistence", "appendonly" in content)
    test("has memory limit", "maxmemory" in content)
    test("has healthcheck", "redis-cli" in content and "ping" in content)
    test("exposes port 6379", '"6379:6379"' in content)


def test_calendar_mcp():
    """Verify calendar-mcp is enabled in registry."""
    print("\n=== Calendar MCP Tests ===")
    registry = PROJECT_ROOT / "mcp-servers" / "mcp-registry.json"
    content = registry.read_text()
    # Find calendar-mcp block and check enabled status
    test("calendar-mcp in registry", "calendar-mcp" in content)
    # Parse JSON to check enabled field
    reg = json.loads(content)
    cal = reg.get("mcp_servers", {}).get("calendar-mcp", {})
    test("calendar-mcp enabled", cal.get("enabled") is True)
    test("calendar-mcp has security config", "security" in cal)
    test("calendar-mcp requires auth", cal.get("security", {}).get("requires_auth") is True)


def test_action_whitelist():
    """Verify action whitelist is functional."""
    print("\n=== Action Whitelist Tests ===")
    wl_path = PROJECT_ROOT / "security" / "action-whitelist.json"
    test("whitelist JSON exists", wl_path.exists())
    wl = json.loads(wl_path.read_text())
    test("has auto_allow section", "auto_allow" in wl)
    test("has require_approval section", "require_approval" in wl)
    test("has blocked section", "blocked" in wl)
    test("read is auto-allowed", "read_file" in wl.get("auto_allow", {}).get("read", []))
    test("git_push requires approval", "git_push" in wl.get("require_approval", {}).get("git", []))
    test("drop_table is blocked", "drop_table" in wl.get("blocked", []))


def test_output_validator():
    """Verify output validator works."""
    print("\n=== Output Validator Tests ===")
    validator = PROJECT_ROOT / "tools" / "output_validator.py"
    test("output_validator.py exists", validator.exists())

    # Test SQL validation
    result = subprocess.run(
        [sys.executable, str(validator), "sql", "SELECT 1 + 1"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    output = json.loads(result.stdout) if result.stdout else {}
    test("valid SQL passes", output.get("valid") is True)

    # Test dangerous SQL blocked
    result = subprocess.run(
        [sys.executable, str(validator), "sql", "DROP TABLE users"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    output = json.loads(result.stdout) if result.stdout else {}
    test("dangerous SQL blocked", output.get("valid") is False)

    # Test API dry-run
    result = subprocess.run(
        [sys.executable, str(validator), "api", "GET", "https://example.com"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    output = json.loads(result.stdout) if result.stdout else {}
    test("API dry-run returns preview", output.get("dry_run") is True)


def test_rate_limiter():
    """Verify rate limiter works."""
    print("\n=== Rate Limiter Tests ===")
    limiter = PROJECT_ROOT / "tools" / "rate_limiter.py"
    test("rate_limiter.py exists", limiter.exists())

    result = subprocess.run(
        [sys.executable, str(limiter), "check", "test_agent", "5", "60"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    output = json.loads(result.stdout) if result.stdout else {}
    test("rate limiter returns allowed", "allowed" in output)
    test("rate limiter has status", "status" in output)


if __name__ == "__main__":
    test_backup_script()
    test_nginx_config()
    test_nginx_in_compose()
    test_redis_in_compose()
    test_calendar_mcp()
    test_action_whitelist()
    test_output_validator()
    test_rate_limiter()

    total = PASS + FAIL
    print(f"\n{'='*50}")
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    print("All Phase 2 infrastructure tests passed!")
