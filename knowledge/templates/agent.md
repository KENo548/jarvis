# Agent Template

Use this template when creating new JARVIS specialist agents.

```markdown
---
name: jarvis-<name>
description: <Brief description of what this agent does and when to use it>
mode: subagent
color: '<hex color>'
permission:
  edit: <allow/deny>
  bash:
    "*": <allow/deny/ask>
    "rm -rf *": ask
    "rm -r *": ask
---

# JARVIS <Name>

You are JARVIS <Name>. <One sentence role description>.

## Capabilities

- <What this agent can do>
- <Key skills>

## Process

```
INPUT → ANALYZE → EXECUTE → VERIFY → OUTPUT
```

## Output Format

```markdown
## <Report Type>: [What was done]

### Summary
[One paragraph]

### Details
[Structured findings]

### Recommendation
[Next steps]
```

## Constraints

- <What this agent does not do>
- <Boundaries and limitations>

---
*Source: <Original source if migrated, or "New agent created for JARVIS v2">*
```

## Naming Conventions

- Agent files: `jarvis-<name>.md`
- Skill directories: `jarvis-<name>/SKILL.md`
- Tool files: `<name>.ts` or `<name>.sh`

## Quality Requirements

- Description: 1-1024 chars, specific enough for routing
- Name: lowercase alphanumeric with single hyphens
- Permissions: minimal necessary for the role
- Provenance: always tag source if migrated from legacy
