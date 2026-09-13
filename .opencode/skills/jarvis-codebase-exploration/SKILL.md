---
name: jarvis-codebase-exploration
description: Fast codebase navigation, pattern finding, file discovery, and code understanding.
license: MIT
metadata:
  domain: engineering
  complexity: low
---

# Codebase Exploration

## What I do

- Fast file discovery by patterns
- Code search and navigation
- Pattern recognition
- Architecture understanding
- Dependency mapping

## When to use me

Use this skill for codebase exploration, file discovery, pattern finding, or architecture understanding.

## Patterns

### File Discovery
```bash
# Find all TypeScript files
find . -name "*.ts" -not -path "*/node_modules/*"

# Find files modified today
find . -mtime -1 -type f
```

### Code Search
```bash
# Find function definitions
grep -rn "function.*handleClick" --include="*.tsx"

# Find imports
grep -rn "from.*react" --include="*.ts"
```

### Architecture Map
```markdown
## Architecture: [Project]

### Entry Points
- src/index.ts → main
- src/app.ts → routes

### Core Modules
- src/auth/ → authentication
- src/api/ → API handlers
- src/db/ → database access

### Key Patterns
- Repository pattern for DB access
- Middleware pattern for auth
- Event-driven for async work
```

## Anti-patterns

- Don't read every file — use search
- Don't skip documentation
- Don't ignore test files

---
*Source: Extracted from wshobson debugging-toolkit agents*
