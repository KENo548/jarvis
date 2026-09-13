---
name: jarvis-deployment
description: CI/CD pipeline management, deployment workflows, and release processes.
license: MIT
metadata:
  domain: infra
  complexity: medium
---

# Deployment

## What I do

- GitHub Actions workflow management
- Vercel deployment configuration
- Render deployment management
- Release workflows
- Environment variable management

## When to use me

Use this skill for deployment, CI/CD, release management, or environment configuration.

## Patterns

### GitHub Actions Deploy
```yaml
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm test
      - run: npm run build
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
```

### Render Deploy
```yaml
services:
  - type: web
    name: api
    runtime: node
    plan: free
    buildCommand: npm install
    startCommand: node server/index.js
    envVars:
      - key: NODE_ENV
        value: production
```

## Anti-patterns

- Don't skip tests before deploy
- Don't hardcode environment variables
- Don't deploy without rollback plan

---
*Source: Extracted from wshobson deployment-strategies, cicd-automation agents*
