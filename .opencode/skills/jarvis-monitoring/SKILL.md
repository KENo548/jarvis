---
name: jarvis-monitoring
description: Observability, logging, metrics, alerting, and SLO/SLI implementation.
license: MIT
metadata:
  domain: infra
  complexity: high
---

# Monitoring

## What I do

- Centralized logging
- Metrics collection and dashboards
- Alerting rules
- SLO/SLI definition
- Distributed tracing

## When to use me

Use this skill for monitoring setup, logging configuration, metrics dashboards, or alerting.

## Patterns

### Structured Logging
```typescript
logger.info('User created', {
  userId: user.id,
  email: user.email,
  timestamp: new Date().toISOString(),
});
```

### Health Check
```typescript
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});
```

### SLO Definition
```
Availability SLO: 99.9% (8.76 hours downtime/year)
Latency SLO: 95% of requests < 200ms
Error rate SLO: < 0.1% of requests
```

## Anti-patterns

- Don't log sensitive data
- Don't skip health checks
- Don't ignore alert fatigue
- Don't set alerts without runbooks

---
*Source: Extracted from wshobson observability-monitoring agents*
