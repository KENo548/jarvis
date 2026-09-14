---
name: jarvis-browser-automation
description: CLI-first browser automation with the Playwright CLI — navigate, click, fill, screenshot, snapshot, and form test. Use the playwright-cli commands (NOT raw playwright npm API) for all web automation. Playwright API knowledge is fallback only.
license: MIT
metadata:
  domain: engineering
  complexity: medium
  tool: playwright
---

# Browser Automation (Playwright CLI)

## What I do

- Navigate URLs and interact with elements
- Capture screenshots and snapshot page state
- Test forms, uploads, dialogs
- Scrape data from web pages
- Test responsive layouts (resize)

## When to use me

Use this skill for web scraping, automated browser testing, screenshot capture, or
form testing. Use the CLI — single-window, silent navigation, human-mirroring cursor.

## Setup requirement

The Playwright browsers must be installed before first use (PC already has them):

```bash
npm ci
npx playwright install chromium
```

## CLI-First Command Reference

Run from the repo root:

**PowerShell (binary resolution):**
```powershell
& "C:\Jarvis\node_modules\.bin\playwright-cli.cmd" <command>
```

**Navigation & interaction:**
```
playwright-cli open <url>
playwright-cli click "<selector>"
playwright-cli fill "<selector>" "<text>"
playwright-cli type "<selector>" "<text>"
playwright-cli press "<key>"
playwright-cli hover "<selector>"
playwright-cli select "<selector>" "<value>"
playwright-cli check "<selector>"
```

**Page state & evidence:**
```
playwright-cli snapshot            # YAML DOM snapshot of current page
playwright-cli screenshot          # full-page PNG to test-results/
```

**Viewport & session control:**
```
playwright-cli resize <width> <height>
playwright-cli navigate <url>
playwright-cli session-list
playwright-cli session-stop
```

## Working Protocol

1. `playwright-cli open <url>` — land on the target.
2. Read the current state with `snapshot` after every significant action.
3. Interact with `click` / `fill` / `type` / `select` as needed.
4. Capture `screenshot` to record visual evidence; store in `test-results/`.
5. After completing the flow, run `session-stop` to release the browser session.
6. Always treat the snapshot as ground truth — re-snapshot before asserting state.

## Evidence & Artifacts

- Screenshots: `test-results/*.png`
- Snapshots: `test-results/*.yaml` (or inline, per session provenance)
- When QA/review needs proof, attach the screenshot path, never a summary.

## Anti-patterns

- Do NOT drive Playwright through the raw npm API (`require('playwright')`) — the
  CLI is the sanctioned hand; API snippets are fallback only for flows the CLI
  cannot express.
- Do NOT claim an interaction succeeded without a snapshot or screenshot.
- Do NOT leave sessions running after a task (always `session-stop`).
- Do NOT use browser automation on the Oracle profile — P0 policy is browser-free
  there; context7 + research covers Oracle needs.

---
*Source: Adapted from JARVIS v3 Tooling Blueprint (playwright-cli integration)*