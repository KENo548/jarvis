#!/bin/bash
# Project Registry Query — resolve project name to path
# Usage: ./project_registry_query.sh <project-name> [platform]
#
# Reads config/projects.json and outputs the resolved path.
# Platform defaults to current OS detection.

set -e

JARVIS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_NAME="${1:?Usage: project_registry_query.sh <project-name> [platform]}"
PLATFORM="${2:-}"

# Auto-detect platform
if [ -z "$PLATFORM" ]; then
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*|Windows_NT) PLATFORM="windows" ;;
    *) PLATFORM="linux" ;;
  esac
fi

# Read and resolve
python3 -c "
import json, sys
with open('$JARVIS_DIR/config/projects.json') as f:
    config = json.load(f)
for project in config.get('projects', []):
    if project['name'] == '$PROJECT_NAME':
        paths = project.get('paths', {})
        path = paths.get('$PLATFORM', paths.get('windows', paths.get('linux', 'UNKNOWN')))
        print(path)
        sys.exit(0)
print(f'Project not found: $PROJECT_NAME', file=sys.stderr)
sys.exit(1)
"
