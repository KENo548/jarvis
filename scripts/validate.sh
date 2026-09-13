#!/bin/bash
# JARVIS Validate — checks structure and config consistency
# Usage: ./scripts/validate.sh

set -e

JARVIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

echo "=== JARVIS Validation ==="
echo "Directory: $JARVIS_DIR"
echo ""

# Check required directories
for dir in ".opencode/agents" ".opencode/skills" ".opencode/tools" ".opencode/instructions" "config" "knowledge" "scripts"; do
  if [ ! -d "$JARVIS_DIR/$dir" ]; then
    echo "MISSING: $dir/"
    ERRORS=$((ERRORS + 1))
  fi
done

# Check required files
for file in ".opencode/opencode.json" "MEMORY.md" "USER.md" "config/projects.json" "config/capabilities.json" "config/security-policy.json" "config/orchestration.md"; do
  if [ ! -f "$JARVIS_DIR/$file" ]; then
    echo "MISSING: $file"
    ERRORS=$((ERRORS + 1))
  fi
done

# Check agent count
AGENT_COUNT=$(ls -1 "$JARVIS_DIR/.opencode/agents/"*.md 2>/dev/null | wc -l)
echo "Agents: $AGENT_COUNT"
if [ "$AGENT_COUNT" -lt 8 ]; then
  echo "WARNING: Expected 8+ agents, found $AGENT_COUNT"
fi

# Check for secrets in config files
echo ""
echo "=== Secret Scan ==="
for file in "$JARVIS_DIR/config/"*.json "$JARVIS_DIR/.opencode/opencode.json"; do
  if [ -f "$file" ]; then
    if grep -qiE "(password|secret|api_key|token|credential)" "$file" 2>/dev/null; then
      # Check if it's a reference like {env:...} or an actual value
      if grep -qP '(?<!\{env:)[A-Za-z0-9]{20,}' "$file" 2>/dev/null; then
        echo "POTENTIAL SECRET in $file"
        ERRORS=$((ERRORS + 1))
      fi
    fi
  fi
done

# Check for stale references
echo ""
echo "=== Stale Reference Check ==="
for file in "$JARVIS_DIR/.opencode/agents/"*.md "$JARVIS_DIR/.opencode/instructions/"*.md; do
  if [ -f "$file" ]; then
    if grep -qi "192 agents\|155 skills\|102 commands\|wshobson\|_opencode/agents" "$file" 2>/dev/null; then
      echo "STALE REFERENCE in $file"
      ERRORS=$((ERRORS + 1))
    fi
  fi
done

# Check JSON validity
echo ""
echo "=== JSON Validity ==="
for file in "$JARVIS_DIR/config/"*.json "$JARVIS_DIR/.opencode/opencode.json"; do
  if [ -f "$file" ]; then
    if ! python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
      echo "INVALID JSON: $file"
      ERRORS=$((ERRORS + 1))
    fi
  fi
done

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS errors found"
  exit 1
else
  echo "PASSED: All checks passed"
fi
