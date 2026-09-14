#!/bin/bash
# Tools Health Check — verify JARVIS toolchain is available and valid (bash)
# Usage: ./tools_health.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARVIS_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
REGISTRY="$JARVIS_DIR/config/tools.json"
BIN_DIR="$JARVIS_DIR/node_modules/.bin"

if [ ! -f "$REGISTRY" ]; then
  echo "ERROR: Registry not found: $REGISTRY" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required" >&2
  exit 1
fi

FAILED=0
TOOL_COUNT=$(jq '.tools | length' "$REGISTRY")

for i in $(seq 0 $((TOOL_COUNT - 1))); do
  ID=$(jq -r ".tools[$i].id" "$REGISTRY")
  LABEL=$(jq -r ".tools[$i].label" "$REGISTRY")
  MIN_VER=$(jq -r ".tools[$i].verification.min_version" "$REGISTRY")

  # bin name: playwright-cli for playwright id
  BIN="$ID"
  [ "$ID" = "playwright" ] && BIN="playwright-cli"
  [ "$ID" = "context7" ] && BIN="ctx7"

  EXE="$BIN_DIR/$BIN"
  if [ ! -f "$EXE" ]; then
    echo "WARNING: $ID ($LABEL) : not found at $EXE — run: npm ci" >&2
    FAILED=$((FAILED + 1))
    continue
  fi

  VERSION=$("$EXE" --version 2>&1 | head -1 || true)
  if echo "$VERSION" | grep -qE '[0-9]+\.[0-9]+\.[0-9]+'; then
    VER=$(echo "$VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    # Compare versions using sort
    if printf '%s\n%s\n' "$MIN_VER" "$VER" | sort -V | head -1 | grep -q "^$MIN_VER$"; then
      echo "$ID: OK (v$VER)"
    else
      echo "WARNING: $ID ($LABEL) : version $VER below minimum $MIN_VER" >&2
      FAILED=$((FAILED + 1))
    fi
  else
    echo "WARNING: $ID ($LABEL) : could not parse version from: $VERSION" >&2
    FAILED=$((FAILED + 1))
  fi
done

if [ "$FAILED" -gt 0 ]; then
  echo "WARNING: $FAILED tool(s) failed health check" >&2
  exit 1
fi

echo "All tools healthy."
exit 0
