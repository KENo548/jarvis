---
name: jarvis-docker
description: Docker containerization, Docker Compose, multi-stage builds, and container orchestration.
license: MIT
metadata:
  domain: infra
  complexity: medium
---

# Docker

## What I do

- Dockerfile creation and optimization
- Docker Compose configuration
- Multi-stage builds
- Container security
- Volume management

## When to use me

Use this skill for Docker containerization, Docker Compose, container builds, or Docker security.

## Patterns

### Multi-stage Build
```dockerfile
# Build stage
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3001
CMD ["node", "dist/index.js"]
```

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
      - app-data:/app/data
    restart: unless-stopped
volumes:
  app-data:
```

## Anti-patterns

- Don't run as root in containers
- Don't use `latest` tags in production
- Don't store secrets in images
- Don't skip .dockerignore

---
*Source: Extracted from wshobson cicd-automation, cloud-infrastructure agents*
