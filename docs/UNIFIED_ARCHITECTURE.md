# JARVIS Unified Architecture: Soul + Body Integration

## Executive Summary

JARVIS (soul) provides cognitive intelligence — 8 specialized agents, capability routing, memory, safety rails. Mark XXXIX (body) provides the physical interface — animated HUD, system monitoring, file handling, voice I/O. This document describes how they merge into a single coherent system.

**Core principle**: The soul is the brain. The body is the senses and actuators. The soul thinks; the body acts and perceives.

---

## Current State Analysis

### What Exists Today

| Component | JARVIS (Soul) | Mark XXXIX (Body) | Overlap |
|-----------|---------------|-------------------|---------|
| Entry point | `sage.py` | `Mark-XXXIX-main/main.py` | — |
| UI | `ui.py` (chat bubbles, pipeline bar) | `Mark-XXXIX-main/ui.py` (HUD, metrics, file drop, log) | Both PyQt6 |
| Agents | 8 specialized (commander, planner, engineer, researcher, memory_coordinator, tool_operator, qa, security) | 1 generic executor with replanning | Different models |
| Tools/Actions | `tools/embodiment/` (18 modules with safety wrappers) | `Mark-XXXIX-main/actions/` (18 modules, no safety) | 16 identical modules |
| LLM Client | `tools/llm_client.py` (multi-provider, Vault, cost tracking) | `Mark-XXXIX-main/config/llm_client.py` (single-provider, requests) | Different quality |
| Memory | Chroma + SQLite + JSON + memory coordinator | JSON only (long_term.json) | Different scope |
| Safety | Asimov, approval queue, action whitelist, kill switch | None | Soul only |
| Observability | Interaction logging, auto-evaluation | None | Soul only |

### Duplication Inventory

**16 nearly identical action modules** (body duplicates soul):
- `browser_control.py`, `code_helper.py`, `computer_control.py`, `computer_settings.py`
- `desktop.py`, `dev_agent.py`, `file_controller.py`, `file_processor.py`
- `flight_finder.py`, `game_updater.py`, `open_app.py`, `reminder.py`
- `send_message.py`, `weather_report.py`, `web_search.py`, `youtube_video.py`

**2 separate LLM clients**, **2 separate UIs**, **2 separate memory systems**, **2 separate agent systems**.

### What the Body Does Better

1. **HUD Canvas** — Animated face with spinning rings, pulse animations, particles, waveform visualization. Visually stunning.
2. **System Metrics** — GPU utilization (NVIDIA/AMD/Intel/macOS), temperature monitoring, uptime, process count.
3. **File Upload** — Drag-and-drop zone with file type detection, size display, category icons.
4. **Setup Overlay** — Provider/model selection UI with live model list fetching and search.
5. **AgentExecutor** — Multi-step execution with automatic replanning, error recovery, and fix generation.

### What the Soul Does Better

1. **Multi-agent specialization** — 8 agents vs 1 generic executor.
2. **Capability registry** — Semantic routing with metric-aware scoring and trust tiers.
3. **Safety rails** — Asimov pre-check, approval queue, action whitelist, kill switch.
4. **Observability** — Interaction logging, auto-evaluation, behavioral signals.
5. **LLM client** — Multi-provider fallback, Vault integration, cost tracking, retry with backoff.
6. **Memory architecture** — Chroma vectors + SQLite state + Neo4j graph + session cache.

---

## Unified Architecture: The 8-Layer Model

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 8 — Unified Interface                                             │
│                                                                          │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐  │
│  │  HUD Canvas      │ │  Chat Panel      │ │  System Metrics          │  │
│  │  (face, rings,   │ │  (message bubbles│ │  (CPU, MEM, NET, GPU,   │  │
│  │   particles,     │ │   pipeline bar,  │ │   TMP, uptime, procs)   │  │
│  │   waveform)      │ │   voice toggle)  │ │                          │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────────┘  │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐  │
│  │  File Drop Zone  │ │  Activity Log    │ │  Setup / Config Overlay  │  │
│  │  (drag-drop,     │ │  (typed entries, │ │  (provider, model, keys) │  │
│  │   browse, icons) │ │   color-coded)   │ │                          │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 7 — Orchestration Bridge                                          │
│                                                                          │
│  bridge.py                                                               │
│  - Routes UI text/voice events → soul agent pipeline                     │
│  - Routes soul results → UI display (chat, log, state)                   │
│  - Manages voice loop lifecycle                                          │
│  - Shared session state (session_id, conversation history)               │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 6 — Agent Fleet                                                   │
│                                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │Commander │ │ Planner  │ │ Engineer │ │Researcher│ │  Memory  │     │
│  │ (routes) │ │ (plans)  │ │ (codes)  │ │ (searches│ │ Coords.  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │  Tool    │ │    QA    │ │ Security │ │ Executor │                   │
│  │Operator  │ │ (tests)  │ │ (audits) │ │(replans) │                   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                   │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 5 — Capability Registry                                           │
│                                                                          │
│  SQLite-backed catalog with semantic routing, metric-aware scoring,      │
│  trust tiers, and routing decision logs.                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 4 — Tool & Embodiment Bus                                         │
│                                                                          │
│  MCP Servers · Browser Control · File Operations · Computer Control      │
│  Voice I/O · Web Search · App Launcher · Desktop · Code Helper           │
│  Weather · YouTube · Flights · Reminders · Messaging · Game Updater      │
│                                                                          │
│  Safety wrappers: file_controller, computer_control, computer_settings   │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 3 — Memory & Knowledge                                            │
│                                                                          │
│  ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ Personal Context  │ │ Vector Store  │ │ State Store   │                │
│  │ (JSON: identity,  │ │ (Chroma DB:   │ │ (SQLite:      │                │
│  │  preferences,     │ │  embeddings,  │ │  tasks, audit,│                │
│  │  relationships)   │ │  semantic     │ │  capabilities,│                │
│  │                   │ │  search)      │ │  routing)     │                │
│  └──────────────────┘ └──────────────┘ └──────────────┘                │
│  ┌──────────────────┐ ┌──────────────┐                                  │
│  │ Knowledge Graph   │ │ Session Cache │                                  │
│  │ (Neo4j: entity    │ │ (Redis:       │                                  │
│  │  relationships)   │ │  ephemeral)   │                                  │
│  └──────────────────┘ └──────────────┘                                  │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 2 — AI Models                                                     │
│                                                                          │
│  Ollama (local, priority 10) → NVIDIA (free, priority 20)               │
│  → OpenAI (priority 30) → Zen (priority 15)                             │
│                                                                          │
│  Features: multi-provider fallback, Vault key management,                │
│  cost tracking, token counting, retry with exponential backoff           │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 1 — Infrastructure                                                │
│                                                                          │
│  Local Machine · Docker Desktop · HashiCorp Vault · Tailscale VPN       │
│  Grafana + Prometheus + Loki · n8n · SearXNG · Neo4j · Chroma          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Communication Protocol

### Design Decision: Direct Function Calls (Synchronous)

**Why not IPC/HTTP/Message Queue?**
- Single-user desktop application — no need for network boundaries
- Latency matters — direct calls are ~0ms overhead
- Simplicity — one process, one memory space
- The body's modules are already imported by the soul (`sage.py` lines 36-180)

### Data Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   User   │────▶│ UI Layer │────▶│  Bridge  │────▶│  Soul's  │
│ (input)  │     │ (body's  │     │          │     │ Commander│
└──────────┘     │  HUD)    │     └──────────┘     └─────┬────┘
                 └──────────┘                             │
                                                    ┌────▼────┐
                 ┌──────────┐     ┌──────────┐      │ Agent   │
                 │ Display  │◀────│  Bridge  │◀─────│ (routes)│
                 │ (chat,   │     │          │      └────┬────┘
                 │  log,    │     └──────────┘           │
                 │  state)  │                      ┌─────▼─────┐
                 └──────────┘                      │ Capability│
                                                   │ Registry  │
                                                   └─────┬─────┘
                                                         │
                              ┌───────────────────────────┼───────────────┐
                              │                           │               │
                        ┌─────▼─────┐             ┌──────▼──────┐  ┌─────▼─────┐
                        │  Tools /  │             │   Memory    │  │   LLM     │
                        │ Embodiment│             │  Systems    │  │  Client   │
                        └───────────┘             └─────────────┘  └───────────┘
```

### Bridge API

```python
# bridge.py — The connective tissue between body and soul

class JarvisBridge:
    """Connects the body's UI to the soul's agent pipeline."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.process_task = None  # Set to soul's process_task function
        self.ui_callbacks = {}    # UI callback functions

    def on_user_input(self, text: str) -> str:
        """Called by UI when user sends a message."""
        # 1. Check Asimov safety
        # 2. Route through soul's agent pipeline
        # 3. Return response for UI display
        return self.process_task(text)

    def on_file_uploaded(self, path: str) -> str:
        """Called by UI when user drops a file."""
        # Format file context and route through pipeline
        msg = f"[FILE_UPLOADED] path={path} ..."
        return self.process_task(msg)

    def on_voice_input(self, text: str) -> str:
        """Called by voice loop when speech is transcribed."""
        return self.process_task(text)

    def update_ui_state(self, state: str):
        """Push state changes to UI (LISTENING, SPEAKING, THINKING)."""
        for cb in self.ui_callbacks.get("state", []):
            cb(state)
```

---

## Unified Entry Point

```python
# jarvis.py — Single entry point for the unified system

"""
Usage:
    python jarvis.py                    # Launch unified GUI
    python jarvis.py --text             # Text-only CLI mode
    python jarvis.py --voice            # Voice mode
    python jarvis.py --test             # Run E2E verification
    python jarvis.py --providers        # List available LLM providers
    python jarvis.py --legacy-ui        # Launch old body UI (during migration)
"""
```

---

## Migration Plan

### Phase 1: Minimal Bridge (Week 1-2)

**Goal**: Soul can talk to body. Both systems functional but connected.

**Deliverables**:
- `jarvis/bridge.py` — Connects soul's `process_task()` to body's UI
- `jarvis/adapters/body_adapter.py` — Wraps body's AgentExecutor as a soul capability
- Body's `JarvisLive._on_text_command()` delegates to soul's `process_task()`
- Both systems share a single `QApplication`
- Verification: launch `main.py`, type command, response routes through soul's agents, displays in body's HUD log

**Files to create**:
```
jarvis/
├── bridge.py                    # NEW: orchestration bridge
├── adapters/
│   └── body_adapter.py          # NEW: wraps body modules as soul tools
```

**Verification criteria**:
- [ ] Typing "hello" in body's UI returns soul's conversational response
- [ ] Typing "search for python tutorials" routes through soul's researcher agent
- [ ] Body's HUD shows agent activity in the log widget
- [ ] No crashes, no import errors

---

### Phase 2: Unified UI (Week 3-4)

**Goal**: Single window combining the best of both UIs.

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER: "J.A.R.V.I.S" — "Cognitive Operating System"  [clock] │
├──────────┬──────────────────────────────┬───────────────────────┤
│  LEFT    │         CENTER               │  RIGHT                │
│          │                              │                       │
│  CPU ███ │    ┌──────────────────┐      │  ▸ ACTIVITY LOG       │
│  MEM ██  │    │                  │      │  ┌─────────────────┐  │
│  NET █   │    │   HUD CANVAS     │      │  │ You: hello      │  │
│  GPU ██  │    │   (face, rings,  │      │  │ Jarvis: Hello!  │  │
│  TMP █   │    │    particles)    │      │  │ ...             │  │
│          │    │                  │      │  └─────────────────┘  │
│  UP 02:34│    └──────────────────┘      │  ───────────────────  │
│  PROC 312│                              │  ▸ FILE UPLOAD        │
│  OS WIN  │    ● LISTENING               │  ┌─────────────────┐  │
│          │    ▁▂▃▂▁▂▃▂▁ (waveform)     │  │ Drop file here  │  │
│  AI CORE │                              │  └─────────────────┘  │
│  ACTIVE  │                              │  ───────────────────  │
│  SEC     │                              │  ▸ COMMAND INPUT      │
│  CLEARED │                              │  [_______________] ▸  │
│          │                              │  🎙 MICROPHONE ACTIVE  │
├──────────┴──────────────────────────────┴───────────────────────┤
│  [F4] Mute  ·  [F11] Fullscreen     JARVIS · CLASSIFIED        │
└─────────────────────────────────────────────────────────────────┘
```

**Components to merge**:
| From Body (keep) | From Soul (keep) | Merge Strategy |
|------------------|------------------|----------------|
| `HudCanvas` | — | Keep as-is (center panel) |
| `MetricBar` (CPU/MEM/NET/GPU/TMP) | `MetricsBar` (CPU/MEM/NET) | Use body's (more complete) |
| `LogWidget` (typed, color-coded) | `MessageBubble` | Keep both: log for system, bubbles for chat |
| `FileDropZone` | — | Keep as-is (right panel) |
| `SetupOverlay` | — | Keep as-is (first-run config) |
| `_SysMetrics` (GPU, temp) | `SysMetrics` | Use body's (more complete) |
| — | Pipeline status bar | Add to header area |
| — | Voice toggle button | Merge into body's microphone button |

**Files to modify**:
```
Mark-XXXIX-main/ui.py  →  jarvis/ui/main_window.py (absorbs soul/ui.py)
sage/ui.py             →  DEPRECATED (functionality moved)
```

**Verification criteria**:
- [ ] Single window launches with all panels visible
- [ ] HUD canvas animates correctly
- [ ] Chat messages appear as bubbles in the right panel
- [ ] File drag-and-drop works
- [ ] System metrics update live (including GPU and temperature)
- [ ] Voice toggle works
- [ ] Setup overlay appears on first run
- [ ] Activity log shows typed, color-coded entries

---

### Phase 3: Full Merge (Week 5-8)

**Goal**: Single codebase, no duplication, clean directory structure.

**New directory structure**:
```
jarvis/
├── jarvis.py                          # Unified entry point
├── bridge.py                          # Orchestration bridge
│
├── ui/                                # Layer 8 — Interface
│   ├── __init__.py
│   ├── main_window.py                 # Unified MainWindow
│   ├── hud_canvas.py                  # Animated HUD (from body)
│   ├── chat_panel.py                  # Message bubbles (from soul)
│   ├── metrics_panel.py               # System metrics (from body)
│   ├── file_drop.py                   # File upload zone (from body)
│   ├── log_widget.py                  # Activity log (from body)
│   ├── setup_overlay.py               # First-run config (from body)
│   └── styles.py                      # Color palette, fonts, constants
│
├── agents/                            # Layer 6 — Agent Fleet
│   ├── __init__.py
│   ├── commander.py                   # Task routing (from soul)
│   ├── planner.py                     # Step planning (from soul)
│   ├── engineer.py                    # Code generation (from soul)
│   ├── researcher.py                  # Web research (from soul)
│   ├── memory_coordinator.py          # Memory management (from soul)
│   ├── tool_operator.py               # Tool dispatch (from soul)
│   ├── qa_agent.py                    # Quality assurance (from soul)
│   ├── security_agent.py              # Security auditing (from soul)
│   ├── executor.py                    # Multi-step execution (from body)
│   └── error_handler.py              # Error recovery (from body)
│
├── tools/                             # Layer 4 — Tool Bus
│   ├── __init__.py
│   ├── embodiment/                    # Physical world tools
│   │   ├── __init__.py
│   │   ├── browser_control.py
│   │   ├── code_helper.py
│   │   ├── computer_control.py
│   │   ├── computer_settings.py
│   │   ├── desktop.py
│   │   ├── dev_agent.py
│   │   ├── file_controller.py
│   │   ├── file_processor.py
│   │   ├── flight_finder.py
│   │   ├── game_updater.py
│   │   ├── open_app.py
│   │   ├── reminder.py
│   │   ├── send_message.py
│   │   ├── vision/
│   │   ├── voice_io.py
│   │   ├── weather_report.py
│   │   ├── web_search.py
│   │   └── youtube_video.py
│   ├── capability_registry.py         # Layer 5 — Routing
│   ├── llm_client.py                  # Layer 2 — AI Models
│   ├── asimov.py                      # Safety layer
│   ├── governance.py                  # Kill switch
│   ├── approval_queue.py              # Human approval
│   ├── audit_log.py                   # Action logging
│   ├── observability/                 # Monitoring
│   │   ├── interaction_logger.py
│   │   ├── auto_eval.py
│   │   └── behavioral_signals.py
│   └── ... (other soul tools)
│
├── memory/                            # Layer 3 — Memory
│   ├── __init__.py
│   ├── personal.py                    # Personal context (from body's memory_manager)
│   ├── knowledge.py                   # Vector + graph memory (from soul)
│   ├── state.py                       # SQLite state (from soul)
│   └── coordinator.py                 # Unified memory access
│
├── config/                            # Configuration
│   ├── __init__.py
│   ├── settings.py                    # Unified settings
│   └── api_keys.json                  # User API keys (from body)
│
├── adapters/                          # Integration adapters
│   ├── __init__.py
│   └── body_adapter.py                # Wraps body modules for soul
│
├── memory_data/                       # Persistent data
│   ├── long_term.json                 # Personal memory (from body)
│   └── sqlite/
│       └── jarvis.db                  # State database
│
├── docs/                              # Documentation
│   ├── ARCHITECTURE.md                # Updated
│   ├── UNIFIED_ARCHITECTURE.md        # This file
│   └── ROADMAP.md                     # Updated
│
├── face.png                           # HUD face image (from body)
└── requirements.txt                   # Merged dependencies
```

**Files to DELETE** (after verification):
```
Mark-XXXIX-main/actions/              # All 16 duplicated action modules
Mark-XXXIX-main/config/llm_client.py  # Superseded by tools/llm_client.py
Mark-XXXIX-main/main.py               # Replaced by jarvis.py
Mark-XXXIX-main/ui.py                 # Absorbed into ui/
Mark-XXXIX-main/agent/planner.py      # Superseded by agents/planner.py
Mark-XXXIX-main/agent/executor.py     # Moved to agents/executor.py
Mark-XXXIX-main/agent/error_handler.py # Moved to agents/error_handler.py
Mark-XXXIX-main/memory/               # Moved to memory/personal.py
sage.py                               # Replaced by jarvis.py
sage/ui.py                            # Absorbed into ui/
```

**Files to KEEP from body** (unique value):
```
face.png                              # HUD face image
config/api_keys.json                  # User's API keys
agent/executor.py                     # Multi-step execution with replanning
agent/error_handler.py                # Error analysis and fix generation
memory/memory_manager.py              # Personal context memory
```

**Verification criteria**:
- [ ] `python jarvis.py` launches the unified system
- [ ] All 8 agents route correctly through capability registry
- [ ] Body's executor is accessible as a capability
- [ ] Memory system reads both personal context and vector knowledge
- [ ] All 18 embodiment tools work through the unified tool bus
- [ ] Asimov safety layer blocks dangerous commands
- [ ] Approval queue prompts for state-changing actions
- [ ] Audit log records all actions
- [ ] No import errors, no duplicate modules

---

### Phase 4: Polish (Week 9-10)

**Goal**: Remove all redundancy, optimize, document.

**Deliverables**:
- Delete `Mark-XXXIX-main/` directory entirely
- Merge system prompts into one comprehensive prompt
- Optimize: single QApplication, single metrics thread, single voice loop
- Performance audit: startup time < 3s, UI response < 100ms
- Update `ARCHITECTURE.md` with the new 8-layer model
- Update `ROADMAP.md` with integration phases
- Create `ADR-001: Soul-Body Unification`
- Write integration tests for the bridge layer
- Document the unified agent fleet capabilities

**Verification criteria**:
- [ ] Zero references to `Mark-XXXIX-main/` in codebase
- [ ] Zero duplicate action modules
- [ ] Single LLM client handles all providers
- [ ] Single memory system with personal + knowledge layers
- [ ] All tests pass
- [ ] Startup time ≤ 3 seconds
- [ ] UI renders at 60fps (HUD canvas)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import path chaos during migration | High | Create `compat.py` shim that re-exports old paths. Phase migration with checkpoints. |
| UI merge breaks PyQt6 rendering | Medium | Test merged UI in isolation first. Keep `--legacy-ui` flag during Phase 2. |
| Memory system conflict (two JSON schemas) | Medium | Body's memory becomes a "personal context" adapter. Migration script imports old data. |
| LLM client incompatibility | Low | Soul's client already supports env vars. Add config file reader as fallback source. |
| Voice loop disruption | Low | Voice IO is already shared (`tools/embodiment/voice_io.py`). No conflict. |
| Agent execution model mismatch | Low | Body's executor becomes a "complex_task" capability. Complementary, not conflicting. |
| Performance regression | Medium | Profile before/after each phase. Single process is faster than two. |

---

## Trade-offs Accepted

| Decision | What We Gain | What We Lose |
|----------|-------------|--------------|
| Soul's agents replace body's executor as primary | Multi-agent specialization, safety rails | Body's elegant simplicity for simple tasks |
| Direct function calls (no IPC) | Zero latency, simplicity | Cannot distribute across machines (acceptable for desktop app) |
| Body's HUD becomes primary UI | Stunning visual identity | Soul's simpler chat UI (but we keep chat bubbles) |
| Single LLM client (soul's) | Vault integration, cost tracking, multi-provider | Body's model browsing UI (but we rebuild it on soul's client) |
| Body's memory becomes "personal context" layer | Rich personal memory with categories | Soul's simpler memory model (but we keep both layers) |

---

## ADR-001: Soul-Body Unification

### Status
Proposed

### Context
JARVIS (soul) and Mark XXXIX (body) were developed independently. They share 16+ identical action modules, both have PyQt6 UIs, both have agent systems, both have memory. The duplication creates maintenance burden and inconsistency. The user's vision is a unified system where the soul provides capabilities and the body provides the physical interface.

### Decision
Merge the two systems using direct function calls (no IPC). The soul becomes the orchestration brain; the body becomes the sensory/actuator layer. The body's UI (HUD + metrics + file upload) becomes the primary interface. The soul's agent fleet and safety rails become the processing backend. A bridge layer connects them.

### Consequences
**Easier**:
- Single codebase to maintain
- Single entry point
- Unified memory and agent systems
- Consistent safety enforcement
- Better visual identity (HUD)

**Harder**:
- Initial migration complexity (4 phases, ~10 weeks)
- Larger UI file (needs module splitting in Phase 4)
- More complex than body's original simple design
- Need to reconcile two config systems

**Risks**:
- Import path migration may break things temporarily
- UI merge may have rendering edge cases
- Memory schema reconciliation needs careful handling

### Alternatives Considered
1. **Keep separate, add HTTP bridge**: Cleaner separation but adds latency and failure modes for a desktop app. Rejected.
2. **Rewrite from scratch**: Clean slate but throws away working code. Rejected — too much risk for no gain.
3. **Body absorbs soul**: Body is simpler but lacks safety rails and multi-agent capability. Rejected — soul is the brain.
