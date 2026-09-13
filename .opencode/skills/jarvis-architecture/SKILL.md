---
name: jarvis-architecture
description: System design, architectural patterns, data flow, and scaling strategies.
license: MIT
metadata:
  domain: engineering
  complexity: high
---

# System Architecture

## What I do

- System design and architecture planning
- Data flow design
- Scaling strategies
- Pattern selection (monolith, microservices, serverless)
- Database schema design
- API design

## When to use me

Use this skill for system design, architecture decisions, data flow planning, or scaling strategies.

## Patterns

### Monolith First
```
Start with a well-structured monolith.
Extract services only when you have clear boundaries and scaling needs.
```

### API Design
```
RESTful:
  GET    /api/resource
  POST   /api/resource
  PUT    /api/resource/:id
  DELETE /api/resource/:id

GraphQL:
  query { resource(id: 1) { field1 field2 } }
  mutation { createResource(input: {...}) { id } }
```

### Data Flow
```
User → API Gateway → Auth → Service → Database
                  ↓
              Cache (Redis)
```

## Anti-patterns

- Don't over-engineer from day one
- Don't skip error handling in architecture
- Don't ignore data consistency

---
*Source: Extracted from wshobson software-architect, c4-architecture agents*
