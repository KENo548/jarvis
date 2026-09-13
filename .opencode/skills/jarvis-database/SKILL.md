---
name: jarvis-database
description: Database design, optimization, SQL patterns, and data modeling.
license: MIT
metadata:
  domain: engineering
  complexity: high
---

# Database

## What I do

- Database schema design
- SQL optimization and indexing
- Query performance analysis
- Data modeling patterns
- Migration strategies

## When to use me

Use this skill for database design, SQL optimization, schema modeling, or performance tuning.

## Patterns

### Indexing Strategy
```sql
-- Index for frequent queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_author ON posts(author_id, created_at);

-- Composite index for multi-column queries
CREATE INDEX idx_orders_status_date ON orders(status, created_at);
```

### Query Optimization
```sql
-- Use EXPLAIN to analyze
EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';

-- Avoid SELECT *
SELECT id, name, email FROM users WHERE active = true;
```

### Data Modeling
```
Users (1) ──── (N) Posts
Posts (1) ──── (N) Comments
Users (N) ──── (N) Roles (through UserRoles)
```

## Anti-patterns

- Don't skip indexes on foreign keys
- Don't use SELECT * in production
- Don't ignore N+1 query problems
- Don't skip database backups

---
*Source: Extracted from wshobson database-design, database-optimization agents*
