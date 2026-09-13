---
name: jarvis-multimodal
description: Visual QA, screenshot comparison, UI review, and before/after analysis.
license: MIT
metadata:
  domain: quality
  complexity: medium
---

# Visual QA

## What I do

- Screenshot capture and comparison
- Visual regression detection
- UI consistency review
- Responsive layout verification
- Before/after analysis

## When to use me

Use this skill for visual QA, screenshot comparison, UI review, or visual regression testing.

## Patterns

### Screenshot Comparison
```markdown
## Visual Review: [Page/Component]

### Before
[screenshot before changes]

### After
[screenshot after changes]

### Issues Found
1. [Visual issue with location]

### Verdict
[PASS/FAIL with reasoning]
```

### Responsive Check
```markdown
## Responsive Layout: [Component]

| Viewport | Status | Issues |
|----------|--------|--------|
| Mobile (375px) | PASS | - |
| Tablet (768px) | PASS | - |
| Desktop (1024px) | FAIL | Spacing issue at header |
```

## Anti-patterns

- Don't rely only on screenshots — test interactions
- Don't skip mobile viewports
- Don't ignore accessibility in visual review

---
*Source: Extracted from gstack design-review capabilities*
