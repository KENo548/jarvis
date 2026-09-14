---
name: jarvis-context7
description: Current authoritative library documentation via Context7 CLI. Use when a task needs current docs for a library (version-gated), API reference, or beyond-cutoff library behavior. Do NOT use for task-state or browser automation.
license: MIT
metadata:
  domain: research
  complexity: low
  tool: context7
---

# Context7 — Current Library Docs

## What I do

- Resolve a library name to a stable Context7 library ID (`ctx7 library`)
- Pull current documentation sections for a pinned library ID (`ctx7 docs`)

## When to use me

Use BEFORE answering any question about a library's current API, version behavior, or
beyond-cutoff features. Triggers: *docs, library, api reference, current version,
how do I use <lib>, what changed in <lib>*.

Rules of engagement:
- Always resolve a library ID first. Passing a raw name to `ctx7 docs` is unreliable.
- For version-sensitive questions (React 19, Vite, Tailwind, Dexie), pull the
  version-specific docs section and cite the library ID.
- If `ctx7 library` returns no result, fall back to web search, do NOT guess the ID.
- Do NOT use for socket/resource-sensitive daemons or long-running processes.

## Usage (project-local CLI)

Bridge allows the CLI to run from the repo's Node toolchain:

**PowerShell:**
```powershell
& "C:\Jarvis\node_modules\.bin\ctx7.cmd" library react
& "C:\Jarvis\node_modules\.bin\ctx7.cmd" docs <library-id> "setState behavior in React 19"
& "C:\Jarvis\node_modules\.bin\ctx7.cmd" list-sources
```

**bash (when a global ctx7 exists on Oracle):**
```bash
ctx7 library react
ctx7 docs <library-id> "query"
```

## Retrieval Protocol

1. `ctx7 library <term>` → capture the resolved library ID.
2. `ctx7 docs <library-id> <query>` → capture the relevant doc section(s).
3. Assert the returned content actually answers the specific question before using it.
4. If content is insufficient, run a second targeted `ctx7 docs` query, then fall
   back to web search. Never output guessed API surface.

Do NOT trim from memory; JARVIS may still compile from the returned docs.

## Anti-patterns

- Do NOT guess library IDs — always resolve first.
- Do NOT use this for non-current docs, local code knowledge, or security research.
- Do NOT call `ctx7 setup --opencode`: it writes a global skill to
  `~/.config/opencode/skills/context7`. This project-local skill is authoritative.

---
*Source: Extracted from JARVIS v3 Tooling Blueprint (context7-cli integration)*