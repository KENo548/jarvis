# SAGE/JARVIS Voice Command Testing Protocol

## Purpose
Shake out the embodiment layer with 25 real voice commands across all 7 Tier 1 tools. Find broken tools, awkward flows, and rough edges before adding more capabilities.

## The Voice Pipeline
```
Microphone (sounddevice) → Whisper STT (port 8081) → SAGE process_task()
→ Commander route → Tool Operator dispatch → Tool execution → Edge TTS output
```

All interactions logged to `C:\jarvis\memory\sqlite\interactions.db` with auto-evaluation.

---

## Pre-Flight Checklist

Before starting the session, verify:

- [ ] Whisper service running: `curl http://localhost:8081/health`
- [ ] Microphone detected: `python -c "from tools.embodiment.voice_io import _find_best_mic; print(_find_best_mic())"`
- [ ] TTS works: `python -c "from tools.embodiment.voice_io import speak; speak('Test successful')"`
- [ ] sage.py starts: `python sage.py --test` passes
- [ ] Database initialized: `python sage.py --stats` returns data
- [ ] Notepad/calculator available (for app launch tests)
- [ ] Desktop has at least 1-2 files or folders visible (for vision tests)
- [ ] An editor window (Notepad or VS Code) has focus for OS control tests
- [ ] Audio output devices working (speakers/headphones)
- [ ] Project is quiet (no other audio playing, mic noise minimal)

### Quick Health Check (run before session)
```powershell
python -c "
from tools.embodiment.voice_io import _find_best_mic, speak
from tests.embodiment_e2e import run_all
print('=== Microphone ==='); _find_best_mic()
print('=== TTS ==='); speak('Ready for testing')
print('=== E2E Gate ==='); run_all()
"
```

---

## Session Structure

**25 commands** organized in 5 rounds, ordered by risk/difficulty:

| Round | Domain | Commands | Risk | Est. Time |
|-------|--------|----------|------|-----------|
| 1 | Voice Pipeline | #1-4 | LOW | 5 min |
| 2 | App Launcher | #5-8 | LOW | 5 min |
| 3 | Screen Vision | #9-12 | LOW | 5 min |
| 4 | Browser Control | #13-16 | MEDIUM | 8 min |
| 5 | File Operations | #17-20 | HIGH | 8 min |
| 6 | OS Control + Settings | #21-25 | HIGH | 8 min |

**Total estimated time**: ~40 minutes

### Flow for Each Command
1. Operator speaks the exact phrase clearly into mic
2. Wait for SAGE to process and respond via TTS
3. Visually verify the tool action happened
4. Record results in the session log
5. Wait 3-5 seconds between commands for system to settle

---

## Test Command List

### ROUND 1: Voice Pipeline (Commands 1-4)
*Purpose: Validate the core voice loop works end-to-end. Warm up Whisper and TTS.*

| # | Spoken Phrase | Expected Behavior | Success Criteria | Risk |
|---|--------------|-------------------|------------------|------|
| 1 | "Hello" | SAGE responds with greeting via TTS | TTS heard, conversational response | LOW |
| 2 | "What time is it?" | SAGE responds with a time reference | TTS heard, response mentions time | LOW |
| 3 | "Repeat after me, testing one two three" | SAGE processes and echoes the phrase | Transcription captures exact words | LOW |
| 4 | "Thank you, that's all" | SAGE acknowledges and closes | TTS heard, polite response | LOW |

### ROUND 2: App Launcher (Commands 5-8)
*Purpose: Test the simplest tool. Proves Sage can launch desktop applications.*

| # | Spoken Phrase | Expected Behavior | Success Criteria | Risk |
|---|--------------|-------------------|------------------|------|
| 5 | "Open calculator" | Calculator window appears | calc.exe visible in taskbar | LOW |
| 6 | "Open notepad" | Notepad window appears | notepad.exe visible in taskbar | LOW |
| 7 | "Open file explorer" | Explorer window opens | explorer window appears | LOW |
| 8 | "Close calculator" | Calculator window closes (via settings) | calc process ends | LOW |

### ROUND 3: Screen Vision (Commands 9-12)
*Purpose: Test Sage can see and understand the screen. May use vision providers.*

| # | Spoken Phrase | Expected Behavior | Success Criteria | Risk |
|---|--------------|-------------------|------------------|------|
| 9 | "What's on my screen?" | SAGE describes current screen contents | Description matches reality | LOW |
| 10 | "How many windows are open?" | SAGE counts visible windows | Count is reasonably accurate (±1) | LOW |
| 11 | "What application is in the top left corner?" | SAGE names the app at that position | App name matches | LOW |
| 12 | "Take a screenshot" | Screenshot saved to desktop | File appears on desktop | LOW |

### ROUND 4: Browser Control (Commands 13-16)
*Purpose: Test Playwright-based browser navigation and interaction.*

| # | Spoken Phrase | Expected Behavior | Success Criteria | Risk |
|---|--------------|-------------------|------------------|------|
| 13 | "Open google.com in the browser" | Browser opens and navigates to Google | Playwright session starts, URL loads | MEDIUM |
| 14 | "Search for weather today" | Browser navigates to search results | Search executed, results visible | MEDIUM |
| 15 | "Go back to the previous page" | Browser navigates back | URL changes to previous | MEDIUM |
| 16 | "Close the browser" | Browser session ends | Playwright session destroyed | MEDIUM |

### ROUND 5: File Operations (Commands 17-20)
*Purpose: Test file create/read/delete with approval gates. HIGH risk — approval gates tested.*

| # | Spoken Phrase | Expected Behavior | Success Criteria | Risk |
|---|--------------|-------------------|------------------|------|
| 17 | "List files on my desktop" | SAGE returns list of desktop files/dirs | Results include real filenames | HIGH |
| 18 | "Create a test file called hello.txt on the desktop" | File created (may need approval) | hello.txt appears on desktop | HIGH |
| 19 | "Read the file hello.txt on the desktop" | SAGE returns contents of hello.txt | Contents shown correctly | HIGH |
| 20 | "Delete the file hello.txt from the desktop" | hello.txt moved to trash (approval gate) | File gone from desktop | HIGH |

### ROUND 6: OS Control + Settings (Commands 21-25)
*Purpose: Test PyAutoGUI keyboard/mouse control and system settings.*

| # | Spoken Phrase | Expected Behavior | Success Criteria | Risk |
|---|--------------|-------------------|------------------|------|
| 21 | "Type the words hello world" | Text typed at cursor position | "hello world" appears in active window | HIGH |
| 22 | "Press enter" | Enter key pressed | New line in active window | HIGH |
| 23 | "Increase volume" | System volume goes up | Volume indicator changes | LOW |
| 24 | "Mute the sound" | System volume muted | Volume indicator shows muted | LOW |
| 25 | "Unmute the sound" | System volume restored | Volume indicator shows unmuted | LOW |

---

## Session Log Template

Create a copy of this table for each session run.

### Session Metadata
```
Date: _________________
Operator: _____________
Start Time: ___________
End Time: _____________
SAGE Version: __________
Whisper Status: OK / FAIL
Mic Device: ___________
```

### Command Results

| # | Spoken Phrase | Domain | Transcription | Pass/Fail | Latency(ms) | Retries | Approval Gate Triggered? | Notes |
|---|--------------|--------|--------------|-----------|-------------|---------|------------------------|-------|
| 1 | "Hello" | Voice | | □ PASS □ FAIL | | | N/A | |
| 2 | "What time is it?" | Voice | | □ PASS □ FAIL | | | N/A | |
| 3 | "Repeat after me..." | Voice | | □ PASS □ FAIL | | | N/A | |
| 4 | "Thank you, that's all" | Voice | | □ PASS □ FAIL | | | N/A | |
| 5 | "Open calculator" | Apps | | □ PASS □ FAIL | | | N/A | |
| 6 | "Open notepad" | Apps | | □ PASS □ FAIL | | | N/A | |
| 7 | "Open file explorer" | Apps | | □ PASS □ FAIL | | | N/A | |
| 8 | "Close calculator" | Apps | | □ PASS □ FAIL | | | N/A | |
| 9 | "What's on my screen?" | Vision | | □ PASS □ FAIL | | | N/A | |
| 10 | "How many windows..." | Vision | | □ PASS □ FAIL | | | N/A | |
| 11 | "What app in top left?" | Vision | | □ PASS □ FAIL | | | N/A | |
| 12 | "Take a screenshot" | Vision | | □ PASS □ FAIL | | | N/A | |
| 13 | "Open google.com" | Browser | | □ PASS □ FAIL | | | □ Yes □ No | |
| 14 | "Search for weather" | Browser | | □ PASS □ FAIL | | | □ Yes □ No | |
| 15 | "Go back" | Browser | | □ PASS □ FAIL | | | □ Yes □ No | |
| 16 | "Close the browser" | Browser | | □ PASS □ FAIL | | | □ Yes □ No | |
| 17 | "List files on desktop" | Files | | □ PASS □ FAIL | | | □ Yes □ No | |
| 18 | "Create hello.txt" | Files | | □ PASS □ FAIL | | | □ Yes □ No | |
| 19 | "Read hello.txt" | Files | | □ PASS □ FAIL | | | □ Yes □ No | |
| 20 | "Delete hello.txt" | Files | | □ PASS □ FAIL | | | □ Yes □ No | |
| 21 | "Type hello world" | OS | | □ PASS □ FAIL | | | □ Yes □ No | |
| 22 | "Press enter" | OS | | □ PASS □ FAIL | | | □ Yes □ No | |
| 23 | "Increase volume" | Settings | | □ PASS □ FAIL | | | □ Yes □ No | |
| 24 | "Mute the sound" | Settings | | □ PASS □ FAIL | | | □ Yes □ No | |
| 25 | "Unmute the sound" | Settings | | □ PASS □ FAIL | | | □ Yes □ No | |

### Session Summary
```
Total Commands:   25
Passed:           ___
Failed:           ___
Success Rate:     ___%
Avg Latency:      ___ ms
Avg Retries:      ___.__
Approval Gates:   ___ triggered
```

### Free-Form Observations
- What broke completely? __________________________________
- What was awkward but worked? __________________________________
- What surprised you? __________________________________
- Suggestions for improvement: __________________________________

---

## Tracking Methodology

### Pass/Fail Criteria

A command **passes** when ALL of the following are true:
1. **Transcription succeeds**: Whisper returns text matching the intent of the spoken phrase
2. **Tool executes**: The targeted tool runs without throwing an exception
3. **Side effect visible**: The expected real-world change happens (app opens, file created, volume changes, etc.)
4. **TTS responds**: Edge TTS speaks a response within 30 seconds

A command **fails** if ANY of:
1. Whisper returns no text or garbled text
2. The tool raises an unhandled exception
3. The action doesn't happen (no app launched, no file created, etc.)
4. TTS times out or errors
5. SAGE routes to the wrong agent/tool

### Metrics to Capture

| Metric | How to Measure | Target |
|--------|---------------|--------|
| **End-to-end latency** | Time from speaking last word to hearing TTS response (stopwatch) | < 10s |
| **Transcription accuracy** | Did the Whisper output match what you said? (subjective 1-3 scale) | 3/3 |
| **Action accuracy** | Did the right tool execute the right action? | Match |
| **Tool dispatch accuracy** | Did SAGE route to the correct tool? | Correct |
| **TTS response quality** | Was the spoken response intelligible and appropriate? | Good |
| **Retry count** | How many times did you need to repeat the command? | 0 |
| **Approval gate behavior** | Did HIGH-risk tools correctly trigger approval? | Correct trigger |
| **Error message clarity** | On failure, was the error message useful? | Useful |

### What the Observability Layer Captures

Every command is automatically logged by `interaction_logger.py` to `C:\jarvis\memory\sqlite\interactions.db`. After the session, query:

```sql
-- All session results
SELECT interaction_id, agent_name, input_text, output_text, 
       latency_ms, success_score, domain, created_at
FROM interactions
WHERE session_id = '<SESSION_ID>'
ORDER BY created_at;

-- Latency distribution
SELECT domain, 
       COUNT(*) as count, 
       ROUND(AVG(latency_ms), 0) as avg_ms,
       ROUND(MAX(latency_ms), 0) as max_ms
FROM interactions
WHERE session_id = '<SESSION_ID>'
GROUP BY domain;

-- Auto-evaluation scores
SELECT i.interaction_id, i.input_text, i.domain,
       json_extract(i.auto_eval, '$.task_completion') as task_score,
       json_extract(i.auto_eval, '$.overall') as overall_score,
       json_extract(i.auto_eval, '$.safety') as safety_score
FROM interactions i
WHERE session_id = '<SESSION_ID>';

-- Failed commands
SELECT input_text, output_text, latency_ms, domain
FROM interactions
WHERE session_id = '<SESSION_ID>'
  AND success_score < 0.45
ORDER BY created_at;
```

### Auto-Evaluation Review

After the session, review the auto-eval results:

```python
python -c "
from tools.observability.auto_eval import get_evaluation_stats
stats = get_evaluation_stats()
print('Overall Quality Distribution:')
for label, pct in stats['percentages'].items():
    print(f'  {label}: {pct}%')
print(f'Average Score: {stats[\"avg_score\"]}')
print(f'Total Interactions: {stats[\"total\"]}')
"
```

The auto-evaluator scores on 7 dimensions (0.0-1.0):
- `task_completion` (30% weight): Did the agent complete the task?
- `safety` (25% weight): Did the agent avoid dangerous behavior?
- `reasoning_quality` (20% weight): Is the reasoning coherent?
- `constraint_following` (10% weight): Did the agent follow instructions?
- `format_adherence` (5% weight): Was the output in expected format?
- `hallucination_risk` (5% weight): Did the agent fabricate anything?
- `tool_validity` (5% weight): Were tool calls valid?

Thresholds: excellent ≥ 0.85, good ≥ 0.65, mediocre ≥ 0.45, poor < 0.45

---

## Post-Session Analysis

### Step 1: Compute Aggregate Results

Run the analysis script after the session:

```python
python -c "
import json, sqlite3
from pathlib import Path

db = Path(r'C:\jarvis\memory\sqlite\interactions.db')
conn = sqlite3.connect(str(db))
conn.row_factory = sqlite3.Row

# Get the most recent session
session = conn.execute(
    'SELECT session_id FROM interactions ORDER BY created_at DESC LIMIT 1'
).fetchone()['session_id']

rows = conn.execute(
    'SELECT * FROM interactions WHERE session_id = ? ORDER BY created_at',
    (session,)
).fetchall()

# Group by domain
from collections import defaultdict
by_domain = defaultdict(list)
for r in rows:
    by_domain[r['domain']].append(dict(r))

print('=== SESSION RESULTS ===')
print(f'Session: {session}')
print(f'Total commands: {len(rows)}')
print()

passed = sum(1 for r in rows if r['success_score'] and r['success_score'] >= 0.45)
print(f'Passed (score >= 0.45): {passed}/{len(rows)}')
print()

for domain, cmds in sorted(by_domain.items()):
    avg_latency = sum(c['latency_ms'] or 0 for c in cmds) / len(cmds)
    avg_score = sum(c['success_score'] or 0 for c in cmds) / len(cmds)
    names = ', '.join(c['input_text'][:40] for c in cmds)
    print(f'{domain.upper():15s} | {len(cmds):2d} cmds | avg {avg_latency:6.0f}ms | score {avg_score:.2f} | {names}')
"
```

### Step 2: Identify Action Items

Classify every failure into one of these categories:

| Category | Definition | Example |
|----------|-----------|---------|
| **Transcription failure** | Whisper didn't hear or understand | Noise, mic issue, quiet voice |
| **Routing failure** | SAGE sent command to wrong tool | "Open calculator" → tried browser |
| **Tool crash** | Tool raised unhandled exception | File not found, import error |
| **Approval gate issue** | Wrong gating (too strict/too lax) | "List files" blocked as HIGH risk |
| **Latency problem** | Command took too long | > 15s end-to-end |
| **TTS failure** | Response wasn't spoken | edge-tts error, ffmpeg missing |
| **UX friction** | Worked but felt wrong | Confusing TTS response, unclear status |

### Step 3: Create Improvement Backlog

For each failure, create a priority-tagged action item:

```markdown
## Improvement Backlog

### P0 (Blocking) — Must fix before next session
- [ ] ...

### P1 (High) — Fix within current sprint
- [ ] ...

### P2 (Medium) — Fix when convenient
- [ ] ...

### P3 (Low) — Nice to have
- [ ] ...
```

### Step 4: Compute Tool-Level Health

For the operator checklist gate, compute:

```python
"""
Gate criteria for embodiment tools:
- Each tool must pass ≥ 3/4 commands in this session
- Voice pipeline must pass ≥ 3/4 warmup commands
- Overall success rate ≥ 80%
- Zero safety incidents (unauthorized destructive operations)
"""
```

### Step 5: Update Embodiment E2E Tests

For any failures found, consider adding automated test cases:

1. Identify the specific failure scenario
2. Add a test case to `tests/embodiment_e2e.py`
3. Mark the test as `@known_failure` if it's a known bug
4. Remove the mark when the fix is verified

---

## Automated Data Capture Script

Save this as `tests/voice_session_report.py` for post-session analysis:

```python
"""Voice testing session report generator."""
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

DB = Path(r"C:\jarvis\memory\sqlite\interactions.db")
THRESHOLD_PASS = 0.45

def generate_report(session_id: str | None = None) -> dict:
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    
    if session_id:
        rows = conn.execute(
            "SELECT * FROM interactions WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
    else:
        session = conn.execute(
            "SELECT session_id FROM interactions ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not session:
            return {"error": "No sessions found"}
        session_id = session["session_id"]
        rows = conn.execute(
            "SELECT * FROM interactions WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
    
    by_domain = defaultdict(list)
    for r in rows:
        by_domain[r["domain"]].append(dict(r))
    
    results = {
        "session_id": session_id,
        "total": len(rows),
        "passed": sum(1 for r in rows if r["success_score"] and r["success_score"] >= THRESHOLD_PASS),
        "domains": {},
    }
    
    for domain, cmds in sorted(by_domain.items()):
        scores = [c["success_score"] or 0 for c in cmds]
        latencies = [c["latency_ms"] or 0 for c in cmds]
        results["domains"][domain] = {
            "count": len(cmds),
            "passed": sum(1 for s in scores if s >= THRESHOLD_PASS),
            "avg_score": round(sum(scores) / len(scores), 3),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 0),
            "max_latency_ms": round(max(latencies), 0),
            "commands": [
                {
                    "input": c["input_text"][:60],
                    "score": c["success_score"],
                    "latency_ms": c["latency_ms"],
                }
                for c in cmds
            ],
        }
    
    conn.close()
    return results

if __name__ == "__main__":
    report = generate_report()
    print(json.dumps(report, indent=2))
```

---

## Quick Reference Card (Print This)

```
╔══════════════════════════════════════════════════════════╗
║            VOICE TESTING — QUICK REFERENCE              ║
╠══════════════════════════════════════════════════════════╣
║                                                        ║
║  PRE-FLIGHT:                                            ║
║  □ Whisper health: curl localhost:8081/health           ║
║  □ sage.py --test passes                                ║
║  □ Mic detected, TTS works                              ║
║                                                        ║
║  SESSION FLOW:                                          ║
║  1. Speak phrase clearly into mic (~15cm distance)      ║
║  2. Wait for TTS response (max 15s)                     ║
║  3. Verify action happened (app, file, volume, etc.)    ║
║  4. Record Pass/Fail + latency + notes in log           ║
║  5. Wait 3-5s between commands                          ║
║                                                        ║
║  25 COMMANDS, 6 ROUNDS:                                 ║
║  Round 1: Voice Pipeline    (#1-4)   LOW   ~5min        ║
║  Round 2: App Launcher      (#5-8)   LOW   ~5min        ║
║  Round 3: Screen Vision     (#9-12)  LOW   ~5min        ║
║  Round 4: Browser Control   (#13-16) MED   ~8min        ║
║  Round 5: File Operations   (#17-20) HIGH  ~8min        ║
║  Round 6: OS + Settings     (#21-25) HIGH  ~8min        ║
║                                                        ║
║  SUCCESS CRITERIA (each command):                       ║
║  ✓ Whisper transcribes correctly                        ║
║  ✓ Right tool executes                                  ║
║  ✓ Side effect visible (app opens, file created, etc.)  ║
║  ✓ TTS responds within 15s                              ║
║                                                        ║
║  PASS GATE (minimum):                                   ║
║  - 20/25 commands pass                                  ║
║  - Each tool passes ≥ 3/4                               ║
║  - Zero safety incidents                                ║
║                                                        ║
║  POST-SESSION:                                          ║
║  □ Run tools/observability/auto_eval.py                 ║
║  □ Query interactions.db for latency distribution       ║
║  □ Classify failures → create improvement backlog       ║
║  □ Update embodiment_e2e.py with regression tests       ║
║                                                        ║
╚══════════════════════════════════════════════════════════╝
```

---

## Appendix: Fail-Safe Procedures

### If voice pipeline stops working mid-session:
```powershell
# Check Whisper
curl http://localhost:8081/health

# Restart Whisper (if Docker)
docker restart jarvis-voice

# Test mic
python -c "from tools.embodiment.voice_io import record_audio, transcribe_whisper; audio = record_audio(max_seconds=5); print(transcribe_whisper(audio))"
```

### If a tool becomes stuck:
```powershell
# Check running background processes
Get-Process | Where-Object { $_.ProcessName -match 'python|playwright|chrome' }

# Force-kill a stuck Sage process
taskkill /F /IM python.exe
```

### Rollback for destructive operations:
```powershell
# If file was deleted accidentally
# Check trash (send2trash) or use git restore for project files

# If volume is stuck muted
python -c "from tools.embodiment.computer_settings import volume_set; volume_set(50)"
```

---

*Protocol designed by Experiment Tracker. Statistical confidence standard: ≥ 80% pass rate required for progression to Tier 2 tools.*
