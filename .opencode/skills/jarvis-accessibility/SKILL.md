---
name: jarvis-accessibility
description: WCAG compliance, screen reader testing, keyboard navigation, and inclusive design.
license: MIT
metadata:
  domain: quality
  complexity: medium
---

# Accessibility

## What I do

- WCAG 2.1 compliance checking
- Screen reader compatibility
- Keyboard navigation testing
- Color contrast analysis
- ARIA attribute usage

## When to use me

Use this skill for accessibility audits, WCAG compliance, screen reader testing, or inclusive design.

## Patterns

### ARIA Labels
```html
<button aria-label="Close dialog">×</button>
<nav aria-label="Main navigation">...</nav>
<div role="alert">Error message</div>
```

### Keyboard Navigation
```tsx
function Modal({ onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);
}
```

### Color Contrast
- Text: minimum 4.5:1 ratio (AA)
- Large text: minimum 3:1 ratio (AA)
- Enhanced: 7:1 ratio (AAA)

## Anti-patterns

- Don't use images without alt text
- Don't rely only on color for information
- Don't skip focus indicators
- Don't ignore screen reader testing

---
*Source: Extracted from wshobson accessibility-compliance agents*
