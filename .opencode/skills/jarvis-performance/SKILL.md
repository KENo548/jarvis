---
name: jarvis-performance
description: Performance optimization, profiling, caching, and load testing.
license: MIT
metadata:
  domain: quality
  complexity: high
---

# Performance

## What I do

- Performance profiling and measurement
- Caching strategies
- Load testing
- Memory optimization
- Bundle size optimization

## When to use me

Use this skill for performance analysis, optimization, caching, or load testing.

## Patterns

### Caching Strategy
```
L1: In-memory (application)
L2: Redis (shared)
L3: CDN (static assets)
L4: Database (query cache)
```

### Measurement
```bash
# Node.js profiling
node --inspect server.js
# Chrome DevTools → Performance tab

# Bundle analysis
npx vite-bundle-visualizer
```

### Lazy Loading
```typescript
// Route-level lazy loading
const Dashboard = lazy(() => import('./Dashboard'));

// Component-level lazy loading
const HeavyChart = lazy(() => import('./HeavyChart'));
```

## Anti-patterns

- Don't optimize without measuring first
- Don't cache without invalidation strategy
- Don't ignore memory leaks
- Don't skip load testing

---
*Source: Extracted from wshobson performance-testing-review agents*
