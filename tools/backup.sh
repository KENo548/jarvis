#!/bin/bash
# =============================================================================
# JARVIS 3-2-1 Backup — Restic + Backblaze B2
# =============================================================================
# Automated encrypted backup following the 3-2-1 rule:
#   3 copies of data, 2 different media, 1 offsite
#
# Setup:
#   1. Install restic: winget install restic (or apt install restic)
#   2. Create Backblaze B2 bucket and application key
#   3. Set environment variables (or create secrets/backup-config.env):
#      export B2_ACCOUNT_ID="your_account_id"
#      export B2_ACCOUNT_KEY="your_account_key"
#      export RESTIC_PASSWORD="your_repos_password"
#      export RESTIC_REPOSITORY="b2:your-bucket-name:jarvis-backups"
#
# Usage:
#   bash tools/backup.sh init     # Initialize backup repository
#   bash tools/backup.sh run      # Run backup now
#   bash tools/backup.sh verify   # Verify latest backup integrity
#   bash tools/backup.sh restore  # Restore from latest backup
#   bash tools/backup.sh list     # List available snapshots
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/secrets/backup-config.env"
LOG_DIR="$PROJECT_DIR/logs"
BACKUP_LOG="$LOG_DIR/backup.log"

# Load config if it exists
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Default paths to back up
BACKUP_PATHS=(
    "$PROJECT_DIR/memory"
    "$PROJECT_DIR/security"
    "$PROJECT_DIR/docs"
    "$PROJECT_DIR/agents"
    "$PROJECT_DIR/tools"
    "$PROJECT_DIR/mcp-servers"
    "$PROJECT_DIR/workflows"
    "$PROJECT_DIR/.github"
)

# Exclude patterns
EXCLUDE_PATTERNS=(
    "*.pyc"
    "__pycache__"
    "*.db-journal"
    "*.db-wal"
    "*.db-shm"
    "node_modules"
    ".venv"
    "chroma-data"
)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$BACKUP_LOG"
}

check_prerequisites() {
    if ! command -v restic &>/dev/null; then
        log "ERROR: restic not found. Install: winget install restic"
        exit 1
    fi

    if [ -z "${RESTIC_REPOSITORY:-}" ]; then
        log "ERROR: RESTIC_REPOSITORY not set. Create secrets/backup-config.env"
        exit 1
    fi

    if [ -z "${RESTIC_PASSWORD:-}" ]; then
        log "ERROR: RESTIC_PASSWORD not set."
        exit 1
    fi
}

init_repo() {
    log "Initializing backup repository..."
    restic init
    log "Repository initialized at $RESTIC_REPOSITORY"
}

run_backup() {
    log "Starting backup..."

    # Build exclude arguments
    EXCLUDE_ARGS=()
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        EXCLUDE_ARGS+=(--exclude="$pattern")
    done

    # Run backup
    restic backup "${BACKUP_PATHS[@]}" "${EXCLUDE_ARGS[@]}" \
        --tag "jarvis" \
        --verbose \
        2>&1 | tee -a "$BACKUP_LOG"

    # Prune old snapshots (keep 7 daily, 4 weekly, 6 monthly)
    restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune

    log "Backup complete."
}

verify_backup() {
    log "Verifying backup integrity..."
    restic check
    log "Verification passed."
}

restore_backup() {
    log "Restoring from latest snapshot..."
    restic latest --tag "jarvis" --path "$PROJECT_DIR"
    log "Restore complete. Check $PROJECT_DIR for restored files."
}

list_snapshots() {
    restic snapshots --tag "jarvis"
}

case "${1:-}" in
    init)
        check_prerequisites
        init_repo
        ;;
    run|backup)
        check_prerequisites
        run_backup
        ;;
    verify|check)
        check_prerequisites
        verify_backup
        ;;
    restore)
        check_prerequisites
        restore_backup
        ;;
    list|snapshots)
        check_prerequisites
        list_snapshots
        ;;
    *)
        echo "Usage: $0 {init|run|verify|restore|list}"
        exit 1
        ;;
esac
