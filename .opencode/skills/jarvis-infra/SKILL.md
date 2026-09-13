---
name: jarvis-infra
description: Infrastructure, Docker, CI/CD, deployment, cloud services, and DevOps patterns.
license: MIT
metadata:
  domain: infra
  complexity: high
---

# Infrastructure & DevOps

## What I do

- Docker containerization
- CI/CD pipeline design
- Cloud deployment (Render, Vercel, Oracle Cloud)
- Nginx configuration
- Monitoring and observability

## When to use me

Use this skill for infrastructure, deployment, Docker, CI/CD, or cloud service configuration.

## Patterns

### Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
    volumes:
      - ./data:/app/data
```

### GitHub Actions
```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
      - run: npm run build
```

### Render Config
```yaml
services:
  - type: web
    name: my-app
    runtime: node
    plan: free
    buildCommand: npm install && npm run build
    startCommand: npm start
```

## Anti-patterns

- Don't hardcode secrets in Dockerfiles
- Don't skip health checks
- Don't use `latest` tags in production

---
*Source: Extracted from wshobson cicd-automation, cloud-infrastructure agents*
