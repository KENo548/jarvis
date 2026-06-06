# ADR-001: Soul-Body Unification

## Status
Proposed

## Context
JARVIS (soul) and Mark XXXIX (body) were developed independently. They share 16+ identical action modules, both have PyQt6 UIs, both have agent systems, both have memory. The duplication creates maintenance burden and inconsistency. The user's vision is a unified system where the soul provides capabilities and the body provides the physical interface.

## Decision
Merge the two systems using direct function calls (no IPC). The soul becomes the orchestration brain; the body becomes the sensory/actuator layer. The body's UI (HUD + metrics + file upload) becomes the primary interface. The soul's agent fleet and safety rails become the processing backend. A bridge layer connects them.

## Consequences

### What becomes easier
- Single codebase to maintain
- Single entry point (`python jarvis.py`)
- Unified memory and agent systems
- Consistent safety enforcement across all actions
- Better visual identity (HUD canvas is stunning)
- Single LLM client with multi-provider fallback and cost tracking

### What becomes harder
- Initial migration complexity (4 phases, ~10 weeks)
- Larger UI file (needs module splitting in Phase 4)
- More complex than body's original simple design
- Need to reconcile two config systems (Vault + JSON files)

### Risks
- Import path migration may break things temporarily
- UI merge may have rendering edge cases
- Memory schema reconciliation needs careful handling
- Performance regression during transition

## Alternatives Considered

### 1. Keep separate, add HTTP bridge
Cleaner separation but adds latency and failure modes for a desktop app. **Rejected.**

### 2. Rewrite from scratch
Clean slate but throws away working code. Too much risk for no gain. **Rejected.**

### 3. Body absorbs soul
Body is simpler but lacks safety rails and multi-agent capability. Soul is the brain. **Rejected.**

## Review History
- Proposed: 2026-06-07 by Software Architect agent
