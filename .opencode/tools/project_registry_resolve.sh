#!/bin/bash
# Project Registry Resolve — resolve project with validation
# Usage: ./project_registry_resolve.sh <project-name> [platform]

set -e

JARVIS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_NAME="${1:?Usage: project_registry_resolve.sh <project-name> [platform]}"
PLATFORM="${2:-}"

# Auto-detect platform
if [ -z "$PLATFORM" ]; then
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*|Windows_NT) PLATFORM="windows" ;;
    *) PLATFORM="linux" ;;
  esac
fi

# Resolve and validate
python3 -c "
import json, sys, os
with open('$JARVIS_DIR/config/projects.json') as f:
    config = json.load(f)
for project in config.get('projects', []):
    if project['name'] == '$PROJECT_NAME':
        paths = project.get('paths', {})
        path = paths.get('$PLATFORM', paths.get('windows', paths.get('linux', 'UNKNOWN')))
        if os.path.exists(path):
            print(path)
            sys.exit(0)
        else:
            print(f'Path does not exist: {path}', file=sys.stderr)
            sys.exit(1)
print(f'Project not found: $PROJECT_NAME', file=sys.stderr)
sys.exit(1)
"
