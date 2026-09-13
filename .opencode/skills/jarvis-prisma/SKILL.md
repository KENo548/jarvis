---
name: jarvis-prisma
description: Prisma ORM schema design, migrations, queries, and database patterns.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# Prisma ORM

## What I do

- Prisma schema design and modeling
- Database migrations
- Query optimization
- Type-safe database access
- Relations and includes

## When to use me

Use this skill when working with Prisma schema, migrations, queries, or database design.

## Patterns

### Schema Design
```prisma
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model Post {
  id        Int      @id @default(autoincrement())
  title     String
  content   String?
  author    User     @relation(fields: [authorId], references: [id])
  authorId  Int
}
```

### Type-safe Queries
```typescript
const user = await prisma.user.findUnique({
  where: { id: 1 },
  include: { posts: true },
});
```

### Migrations
```bash
npx prisma migrate dev --name add_posts_table
npx prisma migrate deploy
```

## Anti-patterns

- Don't use raw SQL when Prisma client works
- Don't skip migration files
- Don't ignore connection pooling

---
*Source: Extracted from wshobson database-design agents*
