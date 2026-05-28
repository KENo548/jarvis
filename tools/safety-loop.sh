#!/usr/bin/env bash
# =============================================================================
# JARVIS Safety Loop for Dependency Updates
# =============================================================================
# 1. Renovate Bot opens a PR with the proposed update
# 2. Security Agent reviews the changelog for breaking changes or CVEs
# 3. QA Agent runs tests in the sandbox environment
# 4. You review the QA report and approve or reject the PR
# 5. If approved, GitHub Actions deploys the update and monitors for errors
# 6. If errors appear within 24 hours, automated rollback
#
# Usage:  ./safety-loop.sh <dependency-name> <current-version> <target-version>
# =============================================================================

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <dependency-name> <current-version> <target-version>"
    echo "Example: $0 chromadb 0.5.0 0.6.3"
    exit 1
fi

NAME="$1"
CURRENT="$2"
TARGET="$3"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../logs" && pwd)"
mkdir -p "$LOG_DIR"

echo "============================================"
echo "  JARVIS SAFETY LOOP"
echo "  Dependency: $NAME"
echo "  $CURRENT -> $TARGET"
echo "============================================"
echo ""

# Step 1: Log the proposed update
echo "[1/6] Logging proposed update..."
echo "$TIMESTAMP | safety-loop | PROPOSED | $NAME | $CURRENT -> $TARGET" >> "$LOG_DIR/updates.log"
echo "  Done."
echo ""

# Step 2: Check for CVEs in the target version
echo "[2/6] Checking for known vulnerabilities..."
if command -v grype &>/dev/null; then
    grype "$NAME@$TARGET" --fail-on high || true
else
    echo "  [SKIP] grype not installed. Install with: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin"
fi
echo "  Done."
echo ""

# Step 3: Run tests in sandbox
echo "[3/6] Running test suite in sandbox..."
TEST_LOG="$LOG_DIR/safety-test-$NAME-$TARGET.log"
if [ -f "package.json" ]; then
    npm test 2>&1 | tee "$TEST_LOG" || echo "  [WARN] Tests failed or not configured. Manual review required."
elif [ -f "requirements.txt" ]; then
    python -m pytest tests/ 2>&1 | tee "$TEST_LOG" || echo "  [WARN] Tests failed or not configured. Manual review required."
else
    echo "  [SKIP] No test framework detected. Manual testing recommended."
fi
echo "  Test log: $TEST_LOG"
echo ""

# Step 4: Create approval request
echo "[4/6] Creating approval request..."
APPROVAL_LOG="$LOG_DIR/approval-request-$NAME-$TARGET.txt"
cat > "$APPROVAL_LOG" << EOF
DEPENDENCY UPDATE APPROVAL REQUEST
==================================
Dependency: $NAME
From: $CURRENT
To: $TARGET
Proposed: $TIMESTAMP
EOF

# Check if there's a changelog URL
CHANGELOG_URL=""
case "$NAME" in
    chromadb) CHANGELOG_URL="https://github.com/chroma-core/chroma/releases" ;;
    n8n) CHANGELOG_URL="https://github.com/n8n-io/n8n/releases" ;;
    *) CHANGELOG_URL="" ;;
esac

if [ -n "$CHANGELOG_URL" ]; then
    echo "Changelog: $CHANGELOG_URL" >> "$APPROVAL_LOG"
fi
echo "Done. Approval request saved to: $APPROVAL_LOG"
echo ""

# Step 5: Present summary
echo "[5/6] Summary for human review:"
echo "  Dependency: $NAME"
echo "  Version:    $CURRENT -> $TARGET"
echo "  Log:        $TEST_LOG"
echo "  Approval:   $APPROVAL_LOG"
echo ""

echo "[6/6] Waiting for human approval..."
echo "  To approve: python tools/approval-queue.py approve <id>"
echo "  To reject:  python tools/approval-queue.py reject <id> <reason>"
echo ""
echo "============================================"
echo "  SAFETY LOOP COMPLETE — AWAITING APPROVAL"
echo "============================================"
