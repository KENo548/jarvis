# File-by-File Integration Map

This document maps every file in both systems to its fate during the merge.

## Legend
- **KEEP** = File stays, possibly modified
- **MOVE** = File moves to new location
- **DELETE** = File is removed (functionality absorbed elsewhere)
- **MERGE** = File content merged into another file
- **CREATE** = New file needed for integration
- **DEPRECATE** = File kept temporarily for backward compatibility, removed in Phase 4

---

## JARVIS Soul Files (tools/, sage.py, ui.py)

| Current Path | Fate | Destination | Notes |
|---|---|---|---|
| `sage.py` | **DELETE** | `jarvis/jarvis.py` | Replaced by unified entry point |
| `ui.py` | **MERGE** | `jarvis/ui/chat_panel.py` | MessageBubbles move to chat panel |
| `tools/llm_client.py` | **KEEP** | `jarvis/tools/llm_client.py` | Supersedes body's LLM client |
| `tools/capability_registry.py` | **KEEP** | `jarvis/tools/capability_registry.py` | Adds body's executor as capability |
| `tools/agents/commander.py` | **KEEP** | `jarvis/agents/commander.py` | No changes |
| `tools/agents/planner.py` | **KEEP** | `jarvis/agents/planner.py` | No changes |
| `tools/agents/engineer.py` | **KEEP** | `jarvis/agents/engineer.py` | No changes |
| `tools/agents/researcher.py` | **KEEP** | `jarvis/agents/researcher.py` | No changes |
| `tools/agents/memory_coordinator.py` | **KEEP** | `jarvis/agents/memory_coordinator.py` | Extended for personal context |
| `tools/agents/tool_operator.py` | **KEEP** | `jarvis/agents/tool_operator.py` | No changes |
| `tools/embodiment/__init__.py` | **KEEP** | `jarvis/tools/embodiment/__init__.py` | No changes |
| `tools/embodiment/browser_control.py` | **KEEP** | `jarvis/tools/embodiment/browser_control.py` | No changes |
| `tools/embodiment/code_helper.py` | **KEEP** | `jarvis/tools/embodiment/code_helper.py` | No changes |
| `tools/embodiment/computer_control.py` | **KEEP** | `jarvis/tools/embodiment/computer_control.py` | No changes |
| `tools/embodiment/computer_settings.py` | **KEEP** | `jarvis/tools/embodiment/computer_settings.py` | No changes |
| `tools/embodiment/desktop.py` | **KEEP** | `jarvis/tools/embodiment/desktop.py` | No changes |
| `tools/embodiment/dev_agent.py` | **KEEP** | `jarvis/tools/embodiment/dev_agent.py` | No changes |
| `tools/embodiment/file_controller.py` | **KEEP** | `jarvis/tools/embodiment/file_controller.py` | No changes |
| `tools/embodiment/file_processor.py` | **KEEP** | `jarvis/tools/embodiment/file_processor.py` | No changes |
| `tools/embodiment/flight_finder.py` | **KEEP** | `jarvis/tools/embodiment/flight_finder.py` | No changes |
| `tools/embodiment/game_updater.py` | **KEEP** | `jarvis/tools/embodiment/game_updater.py` | No changes |
| `tools/embodiment/open_app.py` | **KEEP** | `jarvis/tools/embodiment/open_app.py` | No changes |
| `tools/embodiment/reminder.py` | **KEEP** | `jarvis/tools/embodiment/reminder.py` | No changes |
| `tools/embodiment/send_message.py` | **KEEP** | `jarvis/tools/embodiment/send_message.py` | No changes |
| `tools/embodiment/vision/` | **KEEP** | `jarvis/tools/embodiment/vision/` | No changes |
| `tools/embodiment/voice_io.py` | **KEEP** | `jarvis/tools/embodiment/voice_io.py` | Shared by both systems |
| `tools/embodiment/weather_report.py` | **KEEP** | `jarvis/tools/embodiment/weather_report.py` | No changes |
| `tools/embodiment/web_search.py` | **KEEP** | `jarvis/tools/embodiment/web_search.py` | No changes |
| `tools/embodiment/youtube_video.py` | **KEEP** | `jarvis/tools/embodiment/youtube_video.py` | No changes |
| `tools/asimov.py` | **KEEP** | `jarvis/tools/asimov.py` | Safety layer |
| `tools/governance.py` | **KEEP** | `jarvis/tools/governance.py` | Kill switch |
| `tools/audit_log.py` | **KEEP** | `jarvis/tools/audit_log.py` | Action logging |
| `tools/observability/` | **KEEP** | `jarvis/tools/observability/` | Monitoring |
| `tools/memory_store.py` | **KEEP** | `jarvis/memory/knowledge.py` | Vector + SQLite memory |
| `tools/chroma_client.py` | **KEEP** | `jarvis/tools/chroma_client.py` | Chroma DB client |
| `tools/knowledge_graph.py` | **KEEP** | `jarvis/tools/knowledge_graph.py` | Neo4j integration |
| `tools/vault_client.py` | **KEEP** | `jarvis/tools/vault_client.py` | Secrets management |
| All other `tools/*.py` | **KEEP** | `jarvis/tools/` | Infrastructure tools |

---

## Mark XXXIX Body Files (Mark-XXXIX-main/)

| Current Path | Fate | Destination | Notes |
|---|---|---|---|
| `Mark-XXXIX-main/main.py` | **DELETE** | `jarvis/jarvis.py` | Replaced by unified entry point |
| `Mark-XXXIX-main/ui.py` | **SPLIT** | `jarvis/ui/` (multiple files) | HudCanvas, MetricBar, FileDropZone, LogWidget, SetupOverlay extracted |
| `Mark-XXXIX-main/face.png` | **MOVE** | `jarvis/face.png` | HUD face image |
| `Mark-XXXIX-main/config/api_keys.json` | **MOVE** | `jarvis/config/api_keys.json` | User's API keys |
| `Mark-XXXIX-main/config/llm_client.py` | **DELETE** | — | Superseded by `tools/llm_client.py` |
| `Mark-XXXIX-main/config/__init__.py` | **DELETE** | — | No longer needed |
| `Mark-XXXIX-main/agent/executor.py` | **MOVE** | `jarvis/agents/executor.py` | Unique: replanning + error recovery |
| `Mark-XXXIX-main/agent/error_handler.py` | **MOVE** | `jarvis/agents/error_handler.py` | Unique: error analysis + fix generation |
| `Mark-XXXIX-main/agent/planner.py` | **DELETE** | — | Superseded by `agents/planner.py` |
| `Mark-XXXIX-main/agent/task_queue.py` | **DELETE** | — | Functionality absorbed by bridge |
| `Mark-XXXIX-main/memory/memory_manager.py` | **MOVE** | `jarvis/memory/personal.py` | Personal context memory |
| `Mark-XXXIX-main/memory/config_manager.py` | **DELETE** | — | Absorbed into `config/settings.py` |
| `Mark-XXXIX-main/memory/__init__.py` | **DELETE** | — | No longer needed |
| `Mark-XXXIX-main/actions/browser_control.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/code_helper.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/computer_control.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/computer_settings.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/desktop.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/dev_agent.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/file_controller.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/file_processor.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/flight_finder.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/game_updater.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/open_app.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/reminder.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/screen_processor.py` | **DELETE** | — | Duplicate of `tools/embodiment/vision/` |
| `Mark-XXXIX-main/actions/send_message.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/weather_report.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/web_search.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/actions/youtube_video.py` | **DELETE** | — | Duplicate of `tools/embodiment/` |
| `Mark-XXXIX-main/requirements.txt` | **MERGE** | `jarvis/requirements.txt` | Combined dependencies |
| `Mark-XXXIX-main/setup.py` | **DELETE** | — | No longer needed |
| `Mark-XXXIX-main/readme.md` | **DELETE** | — | Superseded by updated docs |

---

## New Files to Create

| Path | Purpose | Phase |
|---|---|---|
| `jarvis/jarvis.py` | Unified entry point | Phase 1 |
| `jarvis/bridge.py` | Orchestration bridge (body ↔ soul) | Phase 1 |
| `jarvis/adapters/__init__.py` | Adapters package | Phase 1 |
| `jarvis/adapters/body_adapter.py` | Wraps body modules as soul tools | Phase 1 |
| `jarvis/ui/__init__.py` | UI package | Phase 2 |
| `jarvis/ui/main_window.py` | Unified MainWindow | Phase 2 |
| `jarvis/ui/hud_canvas.py` | Animated HUD (from body) | Phase 2 |
| `jarvis/ui/chat_panel.py` | Message bubbles (from soul) | Phase 2 |
| `jarvis/ui/metrics_panel.py` | System metrics (from body) | Phase 2 |
| `jarvis/ui/file_drop.py` | File upload zone (from body) | Phase 2 |
| `jarvis/ui/log_widget.py` | Activity log (from body) | Phase 2 |
| `jarvis/ui/setup_overlay.py` | First-run config (from body) | Phase 2 |
| `jarvis/ui/styles.py` | Color palette, fonts | Phase 2 |
| `jarvis/memory/__init__.py` | Memory package | Phase 3 |
| `jarvis/memory/personal.py` | Personal context (from body) | Phase 3 |
| `jarvis/memory/knowledge.py` | Vector + graph memory (from soul) | Phase 3 |
| `jarvis/memory/state.py` | SQLite state (from soul) | Phase 3 |
| `jarvis/memory/coordinator.py` | Unified memory access | Phase 3 |
| `jarvis/config/__init__.py` | Config package | Phase 3 |
| `jarvis/config/settings.py` | Unified settings | Phase 3 |
| `docs/UNIFIED_ARCHITECTURE.md` | This document | Phase 1 |
| `docs/ADR-001-soul-body-unification.md` | Architecture Decision Record | Phase 1 |

---

## Summary Statistics

| Category | Count |
|---|---|
| Files from soul (KEEP) | ~35 |
| Files from body (MOVE) | 6 |
| Files from body (DELETE) | 24 |
| New files to CREATE | 22 |
| Files to MERGE | 2 |
| **Net result** | ~45 files in unified structure (down from ~70 across two systems) |
