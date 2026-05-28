# User Preferences (saved)

These are your permanent JARVIS settings. Every agent should read this file before giving instructions.

Last updated: 2026-05-27

---

## Who you are (how the AI should talk to you)

- **No coding background.** Explain things in plain language, like teaching a smart friend.
- **Always give beginner-friendly, detailed, step-by-step instructions.** Include exact clicks, menu names, and full paths on Windows.
- **Never assume** you know git, terminals, JSON, or APIs unless you say you have learned them.
- **One step at a time** when possible. After each step, say what success looks like ("you should see…").

---

## Which AI models to use (important)

| Priority | Provider | When to use |
|----------|----------|-------------|
| **Primary** | **Google Gemini** (free tier via Google AI Studio API key) | All normal work: planning, coding help, research summaries |
| **Fallback** | **NVIDIA NIM / build.nvidia.com** (free API key) | When Gemini returns rate-limit errors (429, quota, "resource exhausted") |
| **Do not use** | **Anthropic Claude** (paid) | Unless you explicitly ask to enable it later |

### Model switching rule for agents

1. Start every session on **Gemini** (your default in OpenCode).
2. If you see rate-limit / quota errors, tell the user clearly: *"Gemini hit its limit; switch to NVIDIA for this task."*
3. In OpenCode: type `/models` and pick an **NVIDIA** model (e.g. Nemotron), or run again after keys are set (see setup guide below).
4. Do **not** silently switch to Claude or other paid models.

---

## OpenCode setup (beginner steps — Gemini + NVIDIA)

### Part A — Get your free API keys (one time)

**Gemini (primary)**

1. Open a browser and go to: https://aistudio.google.com/apikey  
2. Sign in with your Google account.  
3. Click **Create API key**.  
4. Copy the key. It usually starts with `AIza…`  
5. Paste it into a password manager (Bitwarden, etc.). **Do not** paste it into chat or email.

**NVIDIA (fallback when Gemini is busy)**

1. Open: https://build.nvidia.com  
2. Create a free account and sign in.  
3. Open your profile / API keys section and **Generate API key**.  
4. Copy the key. It usually starts with `nvapi-…`  
5. Save it in your password manager.

**GitHub (optional for now — needed later for auto-commits)**

1. Open: https://github.com/settings/tokens  
2. **Generate new token (classic)** → enable `repo` scope only if you trust this machine.  
3. Copy `ghp_…` and save in password manager. You can skip this until Phase 1 step "approve a commit."

---

### Part B — Tell OpenCode about your keys

**Method 1 — Easiest (inside OpenCode)**

1. Open **OpenCode** (the app you installed from https://opencode.ai).  
2. **File → Open Folder** → choose:  
   `C:\Users\Admin\Documents\agency-agents-main\jarvis`  
3. In the chat box, type: `/connect` and press Enter.  
4. Search for **Google**, paste your Gemini API key when asked.  
5. Type `/connect` again → search for **NVIDIA**, paste your NVIDIA key.  
6. Type `/models` → pick **Gemini** as your default (e.g. `gemini-2.5-flash` or similar).  
7. Remember the NVIDIA model name you like for fallback (e.g. a Nemotron model).

**Method 2 — Environment file (optional)**

1. Open File Explorer → go to `jarvis\infrastructure\`  
2. If you see `.env.example` but no `.env`, copy `.env.example` and rename the copy to `.env`  
3. Open `.env` in Notepad and set:

   ```
   GOOGLE_API_KEY=AIza-your-real-key-here
   NVIDIA_API_KEY=nvapi-your-real-key-here
   ANTHROPIC_API_KEY=
   ```

4. Leave `ANTHROPIC_API_KEY` empty.  
5. Save and close. **Never** commit `.env` to git.

---

### Part C — When Gemini hits rate limits

1. Read the error — if it mentions **429**, **quota**, or **rate limit**, that is expected on free tiers.  
2. In OpenCode, type: `/models`  
3. Select an **NVIDIA** model from the list.  
4. Retry your last message.  
5. When Gemini resets (often daily), you can switch back with `/models`.

There is no automatic fallback button yet; switching models takes about 10 seconds.

---

## Phase 1 checklist (your path, no Claude)

Use this instead of the blueprint's Anthropic steps.

| Step | What to do | Done? |
|------|------------|-------|
| 1 | Run `setup.ps1` from the `jarvis` folder (creates folders + database) | ☐ |
| 2 | Add **Gemini** + **NVIDIA** keys in OpenCode (`/connect`) | ☐ |
| 3 | Open **only** the `jarvis` folder in OpenCode (not the parent folder) | ☐ |
| 4 | Type: `List MCP servers and confirm they connect` | ☐ |
| 5 | Create Obsidian vault at `memory\obsidian-vault` (optional but useful) | ☐ |
| 6 | Test: `Read README.md and explain it in simple terms` | ☐ |
| 7 | Test approval queue: `python tools\approval-queue.py list` in PowerShell | ☐ |

---

## What to ask the AI (examples)

- "Explain what this folder does like I'm new to programming."  
- "Walk me through opening this project in OpenCode step by step."  
- "Gemini gave a rate limit error — what exactly should I click?"  
- "Which agent should handle building a personal assistant like Iron Man's JARVIS?"

---

## Files that store these preferences

| File | Purpose |
|------|---------|
| `docs/USER_PREFERENCES.md` | This document (human-readable) |
| `config/user-preferences.json` | Machine-readable for scripts |
| `.opencode/opencode.jsonc` | OpenCode default models + disabled paid providers |
| `.cursor/rules/user-preferences.mdc` | Cursor remembers when you edit JARVIS in Cursor |
| `memory/obsidian-vault/USER_PREFERENCES.md` | Same notes inside your knowledge vault |

---

*You remain in charge: the system proposes, you approve before anything dangerous runs.*
