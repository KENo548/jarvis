#!/usr/bin/env bash
# =============================================================================
# JARVIS Emergency Kill Switch — Bash/Linux
# =============================================================================
# Stops all agents, queued actions, and running processes immediately.
# Call this if an agent is misbehaving or if you need to halt all AI activity.
#
# Usage:  ./kill-switch.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$SCRIPT_DIR/../memory/sqlite/jarvis.db"
LOG_PATH="$SCRIPT_DIR/../logs/audit.log"

echo ""
echo "============================================"
echo "   JARVIS EMERGENCY KILL SWITCH ACTIVATED"
echo "============================================"
echo ""

# 1. Write kill signal to database
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" "CREATE TABLE IF NOT EXISTS system_control (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);"
    sqlite3 "$DB_PATH" "INSERT OR REPLACE INTO system_control (key, value, updated_at) VALUES ('kill_switch', 'true', datetime('now'));"
    sqlite3 "$DB_PATH" "UPDATE approval_queue SET status = 'rejected', rejection_reason = 'kill_switch_activated' WHERE status = 'pending';"
    PENDING_COUNT=$(sqlite3 "$DB_PATH" "SELECT changes();")
    echo "[OK] Kill switch signal written to database. ${PENDING_COUNT} pending actions rejected."
else
    echo "[WARN] Database not found at $DB_PATH. Will still stop running processes."
fi

# 2. Kill running agent processes
for PATTERN in "approval-queue" "mcp-" "agent"; do
    if pkill -f "$PATTERN" 2>/dev/null; then
        echo "[OK] Killed processes matching: $PATTERN"
    fi
done

# 3. Write audit log entry
mkdir -p "$(dirname "$LOG_PATH")"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$TIMESTAMP | kill-switch | HUMAN | kill_switch_triggered | Emergency kill switch activated by human | critical" >> "$LOG_PATH"
echo "[OK] Kill switch audit entry written."

echo ""
echo "============================================"
echo "   KILL SWITCH COMPLETE"
echo "   All agents stopped"
echo "   All pending actions rejected"
echo "============================================"
echo ""
echo "To re-enable agents, run: python tools/reset-kill-switch.py"
