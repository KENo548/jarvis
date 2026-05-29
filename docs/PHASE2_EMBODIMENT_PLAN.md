# SAGE Phase 2: Embodiment Integration Plan

## Source: Mark XXXIX (github.com/FatihMakes/Mark-XXXIX)
## Target: SAGE ecosystem (C:\jarvis)

---

## Non-Negotiables
- NO Anthropic, NO Gemini — Ollama primary, OpenAI backup, NVIDIA NIM backup
- Every tool call logged via Phase 1 observability layer
- HIGH-risk tools require approval gate before execution
- One tool at a time — each must work before next begins
- Voice-first: everything starts with voice input
- Capability registry = available + tested + executable (no future intentions)

---

## Steps

### Step 0: Capability Registry (Tier 1 only)
Create tools/embodiment/capability_registry.py with metadata schema:
- name, implementation, description, domain, risk level
- approval_required, sandboxable, rollback_possible, destructive
- inputs, outputs, dependencies, timeout, requires_display, requires_internet

Register only these 7 Tier 1 tools:
1. voice_io
2. open_app
3. screen_processor
4. browser_control
5. file_controller
6. computer_control
7. computer_settings

Add others ONLY when they are fully integrated and tested.

### Step 1: Replace Gemini Backend
Find every google.generativeai / genai call in Mark XXXIX code.
Replace with tools/llm_client.py (Ollama primary).
Files affected: planner.py, executor.py, error_handler.py, code_helper.py,
dev_agent.py, screen_processor.py, main.py
Test: "open calculator" end-to-end through Ollama.

### Step 2: Voice I/O
Integrate sounddevice (mic input) + Whisper service (port 8081) + Edge TTS.
Create tools/embodiment/voice_io.py.
Test: speak command -> Whisper transcribes -> SAGE responds -> TTS speaks.

### Step 3: App Launcher
Copy open_app.py, wrap in Tool Operator.
Simplest tool — proves the pipeline with zero risk.
Test: "open calculator" via voice -> app launches.

### Step 4: Screen Vision (provider pattern)
Create tools/embodiment/vision/ with provider abstraction:
  vision/provider.py      (base class)
  vision/openai_provider.py  (GPT-4o today)
  vision/ollama_provider.py  (local fallback)
  vision/__init__.py      (Vision.analyze_screen(...))
Sage needs eyes before it can act on anything visual.
Test: "what's on my screen" -> description returned.

### Step 5: Browser Control
Copy browser_control.py (Playwright-based).
Depends on vision to verify its own actions.
Test: "open google.com" -> browser navigates.

### Step 6: Replay Test Suite (mandatory gate)
Run all 10 E2E canonical tasks + embodiment tasks.
Catch regressions before adding dangerous tools.
Gate: 9/10 must pass before proceeding to Step 7.

### Step 7: File Operations
Copy file_controller.py. Add approval gate for delete/move.
HIGH risk — approval mandatory.
Test: "list files on desktop" -> file list returned.

### Step 7b: Replay Test Suite (mandatory gate)
Run full replay suite after file operations added.
Confirm no regressions from Step 7.
Gate: 9/10 must pass before proceeding to Step 8.

### Step 8: OS Control
Copy computer_control.py + computer_settings.py.
Highest risk — approval mandatory, test in sandbox first.
Test: "set volume to 50" -> volume changes.

### Step 8b: Replay Test Suite (mandatory gate)
Run full replay suite after OS control added.
Confirm no regressions from Step 8.
Gate: 9/10 must pass before proceeding to Step 9.

### Step 9: HUD Wiring
Wire PyQt6 HUD to SAGE agent pipeline.
Show: active agent, last command, tool executing, system health.
HUD becomes cockpit, not controller.

### Step 10: Memory Migration
Migrate Mark XXXIX JSON memory -> Chroma + SQLite.
Archive old JSON, reroute all reads/writes to Memory Coordinator.
Test: "remember I prefer dark mode" -> stored in Chroma.

### Step 11: Single Entry Point
Create sage.py — the only way to start Sage.
Delete old main.py after one week of stability.
Test: python sage.py -> full system boots.

### Step 12: VPS Deployment
Hetzner CX22 (€4.90/mo). Docker Compose.
Local: HUD + voice (need display/mic).
VPS: agents + memory + infrastructure.
Tailscale VPN connects them.

---

## Tool Integration Order (dependency-aware)
1. voice_io.py (everything starts here)
2. open_app.py (simplest, zero risk)
3. screen_processor.py (Sage needs eyes)
4. browser_control.py (depends on vision)
5. file_controller.py (approval gate required)
6. computer_control.py (highest risk, approval mandatory)
7. computer_settings.py (volume, brightness, WiFi)
8. code_helper.py (sandbox only)
9. dev_agent.py (replace Gemini)
10. web_search.py (replace or alongside SearXNG)
11. youtube_video.py, weather_report.py, flight_finder.py (low risk)
12. send_message.py, reminder.py, game_updater.py (last)

---

## Risk Levels
- LOW: auto-execute, just log (voice, app launcher, vision, settings)
- MEDIUM: log + notify (browser, web search, YouTube)
- HIGH: explicit approval required (files, OS control, code execution, messaging)

---

## Gates (step done when)
- Step 0: capability_registry.py exists, 7 Tier 1 tools registered
- Step 1: "open calculator" works end-to-end through Ollama
- Step 2: voice input -> text -> SAGE -> text -> speech works
- Step 3: app launcher tested with real voice command
- Step 4: vision provider abstraction works with OpenAI + Ollama
- Step 5: browser tested with real voice command
- Step 6: 9/10 E2E tests pass (before dangerous tools)
- Step 7: file operations tested, approval gate verified
- Step 7b: 9/10 E2E tests pass (after files)
- Step 8: OS control tested, approval gate verified
- Step 8b: 9/10 E2E tests pass (after OS control)
- Step 9: HUD shows live agent state
- Step 10: no JSON memory reads/writes remaining
- Step 11: sage.py is only entry point
- Step 12: VPS running, Sage responds when laptop closed
