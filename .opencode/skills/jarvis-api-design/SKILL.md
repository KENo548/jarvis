---
name: jarvis-api-design
description: RESTful API design, GraphQL schemas, API versioning, and API documentation.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# API Design

## What I do

- RESTful API design
- GraphQL schema design
- API versioning strategies
- OpenAPI/Swagger documentation
- Rate limiting and pagination

## When to use me

Use this skill for API design, REST patterns, GraphQL schemas, or API documentation.

## Patterns

### RESTful Design
```
GET    /api/v1/users          → list users
POST   /api/v1/users          → create user
GET    /api/v1/users/:id      → get user
PUT    /api/v1/users/:id      → update user
DELETE /api/v1/users/:id      → delete user
```

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 150,
    "totalPages": 8
  }
}
```

### GraphQL Schema
```graphql
type User {
  id: ID!
  name: String!
  email: String!
  posts: [Post!]!
}

type Query {
  users: [User!]!
  user(id: ID!): User
}

type Mutation {
  createUser(input: CreateUserInput!): User!
}
```

## Anti-patterns

- Don't use verbs in REST endpoints
- Don't skip authentication
- Don't ignore rate limiting
- Don't expose internal IDs

---
*Source: Extracted from wshobson api-scaffolding, backend-api-security agents*
