---
name: jarvis-kubernetes
description: Kubernetes deployment, Helm charts, K8s manifests, and container orchestration.
license: MIT
metadata:
  domain: infra
  complexity: high
---

# Kubernetes

## What I do

- Kubernetes manifest creation
- Helm chart configuration
- Service mesh setup
- K8s security policies
- Cluster management

## When to use me

Use this skill for Kubernetes deployment, Helm charts, K8s configuration, or cluster management.

## Patterns

### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-app:latest
        ports:
        - containerPort: 3001
        resources:
          limits:
            memory: "256Mi"
            cpu: "500m"
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 3001
  type: LoadBalancer
```

## Anti-patterns

- Don't use `latest` tags
- Don't skip resource limits
- Don't ignore pod security
- Don't skip health checks

---
*Source: Extracted from wshobson kubernetes-operations agents*
