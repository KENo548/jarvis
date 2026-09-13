#!/bin/bash
# JARVIS Verify Setup — integration test
# Usage: ./scripts/verify-setup.sh

set -e

JARVIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

echo "=== JARVIS Setup Verification ==="
echo "Directory: $JARVIS_DIR"
echo ""

# 1. Structure check
echo "1. Structure Check"
if bash "$JARVIS_DIR/scripts/validate.sh"; then
  echo "   PASS"
else
  echo "   FAIL"
  ERRORS=$((ERRORS + 1))
fi

# 2. OpenCode config check
echo ""
echo "2. OpenCode Config Check"
if [ -f "$JARVIS_DIR/.opencode/opencode.json" ]; then
  if python3 -c "import json; json.load(open('$JARVIS_DIR/.opencode/opencode.json'))" 2>/dev/null; then
    echo "   PASS: opencode.json valid"
  else
    echo "   FAIL: opencode.json invalid JSON"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "   FAIL: opencode.json missing"
  ERRORS=$((ERRORS + 1))
fi

# 3. Agent count check
echo ""
echo "3. Agent Count"
AGENT_COUNT=$(ls -1 "$JARVIS_DIR/.opencode/agents/"*.md 2>/dev/null | wc -l)
echo "   Found $AGENT_COUNT agents"
if [ "$AGENT_COUNT" -ge 8 ]; then
  echo "   PASS"
else
  echo "   FAIL: Expected 8+ agents"
  ERRORS=$((ERRORS + 1))
fi

# 4. Skill count check
echo ""
echo "4. Skill Count"
SKILL_COUNT=$(ls -1d "$JARVIS_DIR/.opencode/skills/"*/ 2>/dev/null | wc -l)
echo "   Found $SKILL_COUNT skills"
if [ "$SKILL_COUNT" -ge 12 ]; then
  echo "   PASS"
else
  echo "   WARNING: Expected 12+ skills, found $SKILL_COUNT"
fi

# 5. Config files check
echo ""
echo "5. Config Files"
for file in projects.json capabilities.json security-policy.json orchestration.md; do
  if [ -f "$JARVIS_DIR/config/$file" ]; then
    echo "   PASS: config/$file"
  else
    echo "   FAIL: config/$file missing"
    ERRORS=$((ERRORS + 1))
  fi
done

# 6. Knowledge files check
echo ""
echo "6. Knowledge Files"
for file in MEMORY.md USER.md; do
  if [ -f "$JARVIS_DIR/$file" ]; then
    echo "   PASS: $file"
  else
    echo "   FAIL: $file missing"
    ERRORS=$((ERRORS + 1))
  fi
done

# 7. No secrets check
echo ""
echo "7. Secret Scan"
SECRET_FOUND=0
for file in $(find "$JARVIS_DIR/config" "$JARVIS_DIR/.opencode" -name "*.json" -o -name "*.md" 2>/dev/null); do
  if grep -qiE "(password|secret|api_key|token|credential)" "$file" 2>/dev/null; then
    if grep -qP '(?<!\{env:)[A-Za-z0-9]{20,}' "$file" 2>/dev/null; then
      echo "   POTENTIAL SECRET: $file"
      SECRET_FOUND=1
    fi
  fi
done
if [ "$SECRET_FOUND" -eq 0 ]; then
  echo "   PASS: No secrets found"
else
  echo "   WARNING: Review potential secrets"
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "=== FAILED: $ERRORS errors ==="
  exit 1
else
  echo "=== PASSED: All checks passed ==="
fi
