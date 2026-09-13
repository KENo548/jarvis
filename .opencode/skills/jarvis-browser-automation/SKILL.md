---
name: jarvis-browser-automation
description: Web scraping, automated browser testing, screenshot capture, and form interaction using Playwright.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# Browser Automation

## What I do

- Navigate URLs and interact with elements
- Capture screenshots and compare before/after
- Test forms, uploads, dialogs
- Scrape data from web pages
- Test responsive layouts

## When to use me

Use this skill for web scraping, automated browser testing, screenshot capture, or form testing.

## Patterns

### Page Navigation
```javascript
const { chromium } = require('playwright');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('https://example.com');
```

### Element Interaction
```javascript
await page.click('button#submit');
await page.fill('input[name="email"]', 'test@example.com');
await page.selectOption('select#role', 'admin');
```

### Screenshot
```javascript
await page.screenshot({ path: 'screenshot.png', fullPage: true });
```

### Form Testing
```javascript
await page.goto('/login');
await page.fill('#email', 'user@example.com');
await page.fill('#password', 'password');
await page.click('#login-button');
await page.waitForURL('/dashboard');
```

## Anti-patterns

- Don't hardcode selectors — use data-testid
- Don't skip wait for network idle
- Don't ignore mobile viewports

---
*Source: Extracted from gstack browse capabilities*
