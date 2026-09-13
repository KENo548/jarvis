---
name: jarvis-testing
description: Test strategy, unit testing, integration testing, E2E testing, and test automation.
license: MIT
metadata:
  domain: quality
  complexity: medium
---

# Testing

## What I do

- Test strategy design
- Unit testing (Jest, Vitest, pytest)
- Integration testing
- E2E testing (Playwright, Cypress)
- Test automation

## When to use me

Use this skill for test strategy, writing tests, test automation, or test debugging.

## Patterns

### Unit Test
```typescript
describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName prop="value" />);
    expect(screen.getByText('expected')).toBeInTheDocument();
  });
});
```

### Integration Test
```typescript
describe('API /users', () => {
  it('should return user list', async () => {
    const response = await request(app).get('/api/users');
    expect(response.status).toBe(200);
    expect(response.body).toBeInstanceOf(Array);
  });
});
```

### E2E Test
```typescript
test('user can login', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#email', 'user@example.com');
  await page.fill('#password', 'password');
  await page.click('#login');
  await expect(page).toHaveURL('/dashboard');
});
```

## Anti-patterns

- Don't test implementation details — test behavior
- Don't skip edge cases
- Don't use real data in tests
- Don't ignore flaky tests

---
*Source: Extracted from wshobson unit-testing, tdd-workflows agents*
