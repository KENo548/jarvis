---
name: jarvis-git
description: Git operations, branching strategies, commit conventions, and collaboration workflows.
license: MIT
metadata:
  domain: engineering
  complexity: low
---

# Git Workflow

## What I do

- Git operations (commit, branch, merge, rebase)
- Branch strategy (main/staging/feature)
- Commit message conventions
- PR creation and review
- Conflict resolution

## When to use me

Use this skill for any Git operations, branching decisions, or collaboration workflows.

## Patterns

### Feature Branch Workflow
```bash
git checkout -b feature/my-feature
# work
git add -A
git commit -m "feat: add new feature"
git push -u origin feature/my-feature
# create PR
```

### Commit Convention
```
feat: new feature
fix: bug fix
docs: documentation
style: formatting
refactor: code restructuring
test: adding tests
chore: maintenance
```

### Safe Merge
```bash
git fetch origin
git checkout main
git merge --no-ff feature/my-feature
git push origin main
```

## Anti-patterns

- Don't force-push to shared branches
- Don't commit secrets or credentials
- Don't use `git reset --hard` without backup
- Don't skip `.gitignore`

---
*Source: Extracted from wshobson git-pr-workflows agents*
