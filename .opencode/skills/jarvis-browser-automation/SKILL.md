---
name: jarvis-browser-automation
description: CLI-first browser automation with the Playwright CLI (playwright-cli) — navigate, click, fill, screenshot, snapshot, and form test. MANDATORY session lifecycle: every open must be paired with a close inside the SAME bounded invocation. Never treat a persistent browser session as a hung tool.
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

Use for web scraping, automated browser testing, screenshot capture, or form
testing. Windows profile only — Oracle is browser-free (P0 policy).

## Setup requirement

Browsers must be installed before first use (PC already has them):

```bash
npm ci
npx playwright install chromium
```

## CRITICAL: session lifecycle rule

`playwright-cli open` starts a **persistent browser process** that keeps running
until `close`. If `open` is issued as a standalone tool call, the shell runner
waits on that persistent process and the session looks hung.

**Therefore: run the ENTIRE lifecycle inside ONE bounded bash invocation.**

```
CREATE/OPEN SESSION
→ NAVIGATE
→ SNAPSHOT/INSPECT
→ INTERACT AS NEEDED
→ SCREENSHOT/EVIDENCE
→ CLOSE SESSION
→ VERIFY CLEANUP
→ RETURN RESULT
```

- Use a **fresh, unique session name** per verification (e.g. `bv-<unix-ts>`);
  never reuse a name across tasks.
- Pass the session with the space form `-s $SESSION` (this interpolates
  variables; the `-s=$SESSION` form passes the literal variable name).
- Use the **identical session token** for `open`, every step, and `close`.
- Wrap steps so `close` runs even if an earlier step fails (cleanup is
  mandatory on failure paths).
- After `close`, run `list` and confirm `(no browsers)` before reporting.
- Bounded waits: every playwright-cli invocation must carry a timeout
  (default 60s in psi; raise to 90s only for slow pages).
- Never kill unrelated browser processes. Cleanup uses the CLI's own
  `close`/`close-all`/`kill-all` commands only.

## Commands (match the ACTUAL CLI 0.1.x — verified against --help)

Navigation:
```
playwright-cli [-s <session>] open [url]     # open browser, goto url
playwright-cli [-s <session>] goto <url>     # navigate (NOT "navigate")
playwright-cli [-s <session>] reload
```

Inspect:
```
playwright-cli [-s <session>] snapshot [target]      # YAML DOM snapshot
playwright-cli [-s <session>] find [text]            # search snapshot for text
playwright-cli [-s <session>] console [min-level]    # surface errors to QA
```

Interact:
```
playwright-cli [-s <session>] click <target>
playwright-cli [-s <session>] fill <target> <text>
playwright-cli [-s <session>] type <text>
playwright-cli [-s <session>] press <key>
playwright-cli [-s <session>] hover <target>
playwright-cli [-s <session>] select <target> <value>
playwright-cli [-s <session>] check <target>
playwright-cli [-s <session>] resize <width> <height>
```

Evidence:
```
playwright-cli [-s <session>] screenshot [target]     # PNG
```

Session lifecycle (correct names — NOT "session-list"/"session-stop"):
```
playwright-cli list          # list sessions
playwright-cli -s <name> close        # close one session
playwright-cli close-all     # close all sessions
playwright-cli kill-all      # force-kill stale sessions
```

## Working protocol (single invocation)

Build the whole flow as sequential playwright-cli calls joined in ONE bash
command (PowerShell: separate with `;`, capture output, always end with close
+ list verification):

```powershell
$pc = "C:\Jarvis\node_modules\.bin\playwright-cli.cmd"
$SESSION = "bv-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
& $pc -s $SESSION open "http://127.0.0.1:5173/login"
& $pc -s $SESSION snapshot
& $pc -s $SESSION screenshot
& $pc -s $SESSION close
& $pc list
```

1. `open <url>` — land on the target (headless, isolated in-memory profile —
   never a personal Chrome profile).
2. `snapshot` after every significant action; treat the YAML as ground truth.
3. Interact with `click`/`fill`/`type`/`select` as needed; re-snapshot after
   each action.
4. `screenshot` to keep visual evidence; move/point to `test-results/`.
5. `close`, then `list` and verify `(no browsers)`.
6. If any step fails, still run `close` (and `close-all` if needed) before
   reporting the failure. Report console errors to QA.

## Evidence & artifacts

- Screenshots: move to `test-results/<scenario>/<step>.png`
- Snapshots: `.yml` alongside (or inline per session provenance)
- Console log: capture via `console` command; report errors to QA

## Anti-patterns

- Do NOT issue `open` as a standalone tool call expecting a prompt return —
  it is a persistent session; chain the whole lifecycle in one invocation.
- Do NOT use `navigate` / `session-list` / `session-stop` — they do not exist
  in CLI 0.1.x; real names are `goto` / `list` / `close`.
- Do NOT reuse a session name across tasks.
- Do NOT claim an interaction succeeded without a snapshot or screenshot.
- Do NOT leave sessions running; always close and verify.
- Do NOT `kill-all` or kill OS processes indiscriminately; only the CLI's
  own session-kill commands, and only for stale JARVIS sessions.
- Do NOT use playback on the Oracle profile — P0 policy is browser-free there.

---
*Source: JARVIS v3 P0 — corrected lifecycle (verified against playwright-cli 0.1.19 --help, 2026-09-14)*