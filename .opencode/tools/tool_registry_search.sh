#!/bin/bash
# Tool Registry Search — find tool by trigger keyword (bash)
# Usage: ./tool_registry_search.sh <keyword>

set -euo pipefail

KEYWORD="${1,,}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARVIS_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONFIG="$JARVIS_DIR/config/tools.json"

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required" >&2
  exit 1
fi

RESULTS=$(jq --arg kw "$KEYWORD" -r '
  .tools[] |
  select(
    (.id | ascii_downcase | contains($kw)) or
    (.label // "" | ascii_downcase | contains($kw)) or
    (.purpose // "" | ascii_downcase | contains($kw)) or
    (.agents // [] | any(. | ascii_downcase | contains($kw))) or
    (.cli_commands // [] | any(. | ascii_downcase | contains($kw)))
  ) |
  "\(.id): \(.label) [\(.platforms | join(", "))] [agents: \(.agents | join(", "))] [type: \(.type)]"
' "$CONFIG")

if [ -n "$RESULTS" ]; then
  echo "$RESULTS"
  exit 0
else
  echo "ERROR: No tool found for: $1" >&2
  exit 1
fi
