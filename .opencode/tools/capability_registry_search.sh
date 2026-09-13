#!/bin/bash
# Capability Registry Search — find skill by trigger keyword
# Usage: ./capability_registry_search.sh <keyword>

set -e

JARVIS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
KEYWORD="${1:?Usage: capability_registry_search.sh <keyword>}"

python3 -c "
import json, sys
with open('$JARVIS_DIR/config/capabilities.json') as f:
    config = json.load(f)
keyword = '$KEYWORD'.lower()
matches = []
for cap in config.get('capabilities', []):
    triggers = [t.lower() for t in cap.get('triggers', [])]
    if keyword in triggers or any(keyword in t for t in triggers):
        matches.append(cap)
if matches:
    for m in matches:
        print(f'{m[\"id\"]}: {m[\"name\"]} → skill: {m[\"skill\"]}')
else:
    print(f'No capability found for: $KEYWORD')
    sys.exit(1)
"
