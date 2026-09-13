---
name: jarvis-typescript
description: TypeScript advanced types, patterns, type safety, and modern JavaScript.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# TypeScript

## What I do

- Advanced TypeScript types
- Type narrowing and guards
- Generic patterns
- Module organization
- TypeScript strict mode

## When to use me

Use this skill for TypeScript type design, type safety, generic patterns, or type debugging.

## Patterns

### Discriminated Unions
```typescript
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: string };

function handle(result: Result<User>) {
  if (result.success) {
    console.log(result.data); // TypeScript knows this is User
  } else {
    console.log(result.error); // TypeScript knows this is string
  }
}
```

### Type Guards
```typescript
function isString(value: unknown): value is string {
  return typeof value === 'string';
}
```

### Utility Types
```typescript
type Partial<T> = { [K in keyof T]?: T[K] };
type Required<T> = { [K in keyof T]-?: T[K] };
type Pick<T, K extends keyof T> = { [P in K]: T[P] };
type Omit<T, K extends keyof T> = Pick<T, Exclude<keyof T, K>>;
```

### Strict Mode Config
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true
  }
}
```

## Anti-patterns

- Don't use `any` — use `unknown` and narrow
- Don't ignore strict mode errors
- Don't use type assertions without validation

---
*Source: Extracted from wshobson javascript-typescript agents*
