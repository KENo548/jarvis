---
name: jarvis-project-transfer
description: Project migration, codebase transfer, and environment setup across machines.
license: MIT
metadata:
  domain: engineering
  complexity: high
---

# Project Transfer

## What I do

- Project migration between machines
- Environment setup and configuration
- Dependency installation and verification
- Configuration adaptation
- Transfer validation

## When to use me

Use this skill for project migration, environment setup, or codebase transfer between machines.

## Patterns

### Transfer Checklist
```markdown
## Transfer Checklist

### Pre-transfer
- [ ] Document current environment
- [ ] List all dependencies
- [ ] Export configurations
- [ ] Note environment variables

### Transfer
- [ ] Copy source code
- [ ] Install dependencies
- [ ] Adapt configurations
- [ ] Set up environment variables

### Post-transfer
- [ ] Verify builds work
- [ ] Run tests
- [ ] Check integrations
- [ ] Document new environment
```

### Environment Adaptation
```bash
# Detect platform
if [[ "$OSTYPE" == "msys" ]]; then
  # Windows
  CONFIG_PATH="C:\\..."
else
  # Linux/Mac
  CONFIG_PATH="/home/..."
fi
```

## Anti-patterns

- Don't hardcode paths
- Don't skip validation after transfer
- Don't ignore platform differences

---
*Source: Extracted from wshobson ship-mate agents*
