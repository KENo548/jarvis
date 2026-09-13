# Skill Template

Use this template when creating new JARVIS specialist skills.

```markdown
---
name: jarvis-<name>
description: <Brief description for the skill tool listing>
license: MIT
metadata:
  domain: <engineering/research/quality/security/infra>
  complexity: <low/medium/high>
---

# <Skill Name>

## What I do

- <Specific capability>
- <When this skill applies>

## When to use me

Use this skill when: <specific trigger scenarios>

## Process

```
STEP 1 → STEP 2 → STEP 3 → OUTPUT
```

## Patterns

### Pattern 1: <Name>
<Description and implementation>

### Pattern 2: <Name>
<Description and implementation>

## Anti-patterns

- <What NOT to do>
- <Common mistakes>

## References

- <Links to documentation, examples>

---
*Source: <Original source if migrated, or "New skill created for JARVIS v2">*
```

## Naming Conventions

- Directory: `jarvis-<name>/`
- File: `SKILL.md` (must be all caps)
- Name: lowercase alphanumeric with single hyphens, 1-64 chars
- Description: 1-1024 chars, specific enough for agent routing

## Placement

- Project-local: `.opencode/skills/<name>/SKILL.md`
- Global: `~/.config/opencode/skills/<name>/SKILL.md`

## Quality Requirements

- Frontmatter: name (required), description (required)
- Provenance: always tag source if migrated from legacy
- Keep skills focused: one skill = one capability domain
