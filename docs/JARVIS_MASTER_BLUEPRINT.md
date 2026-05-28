J.A.R.V.I.S. AI ECOSYSTEM — MASTER BLUEPRINT

This repository file is a canonical copy of the J.A.R.V.I.S. AI Ecosystem Blueprint.

Important user preference: No Anthropic or Gemini API usage. Prefer fully open-source
and local-first tools; avoid paid APIs or subscription services unless absolutely
necessary and explicitly approved.

See the companion Phase 1 checklist for a local-only setup: ../jarvis/PHASE1_LOCAL.md

---

This document is the master blueprint summary. The full, original blueprint lives
in the repository's docs and design notes; use this file as the single source of
truth for policy decisions and high-level architecture decisions.

Key decisions (user preferences):

- Primary models: local LLMs only (llama.cpp, local Mistral/Llama variants, text-generation-webui, or similar).
- Avoid cloud LLM API keys (Anthropic, Gemini, OpenAI) by default.
- Prefer open-source toolchain: Chroma, SQLite, Redis, Playwright, n8n (self-hosted), Grafana/Prometheus, Falco.
- Human approval gate required for any irreversible action (git push, deploy, DB write, external API modifications).

Phased roadmap and folder structure are maintained in the repo; use the Phase 1
file in `jarvis/` for immediate setup steps.

For implementation tasks (MCP servers, sandboxes, local LLM runners), follow the
Phase 1 checklist and create isolated Docker containers for each service. Use
the approval queue stored in SQLite for all state-changing actions.

If you'd like, I can now:
- scaffold MCP server stubs for local-only tools (filesystem, sqlite, fetch)
- create a Docker Compose example to run Chroma and a local LLM runner
- implement a minimal approval-queue in `jarvis/` using SQLite

Tell me which of these you'd like me to do next, or I'll proceed with scaffolding the MCP stubs.
