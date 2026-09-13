#!/bin/bash
# JARVIS Git-Aware Sync Helper
# Usage: ./scripts/sync.sh [pull|push|status]
#
# This is NOT file synchronization.
# It uses Git as the sync layer between PC and Oracle.

set -e

MODE="${1:-status}"
JARVIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$JARVIS_DIR"

# Check for uncommitted work first
check_uncommitted() {
  if ! git diff --quiet 2>/dev/null; then
    echo "WARNING: Uncommitted changes in working tree"
    git diff --stat
    return 1
  fi
  if ! git diff --cached --quiet 2>/dev/null; then
    echo "WARNING: Staged but uncommitted changes"
    git diff --cached --stat
    return 1
  fi
  return 0
}

case "$MODE" in
  status)
    echo "=== JARVIS Git Status ==="
    git status
    echo ""
    echo "=== Remote Status ==="
    git fetch --dry-run 2>&1 || echo "(fetch failed — check remote config)"
    ;;

  pull)
    echo "=== JARVIS Git Pull ==="
    if ! check_uncommitted; then
      echo "ABORT: Commit or stash changes before pulling"
      exit 1
    fi
    git fetch
    git status
    echo ""
    echo "Ready to pull. Run: git pull"
    ;;

  push)
    echo "=== JARVIS Git Push ==="
    if ! check_uncommitted; then
      echo "ABORT: Commit changes before pushing"
      exit 1
    fi
    git status
    echo ""
    echo "Ready to push. Run: git push"
    ;;

  *)
    echo "Usage: ./scripts/sync.sh [pull|push|status]"
    exit 1
    ;;
esac
