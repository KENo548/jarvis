Summary of automated fixes applied to fully implement Phase 1–3 (local-first)

Applied changes:

- Replaced cloud LLM model references in all agent `config.json` files with `local/llama.cpp` (these are placeholders that route to local runners via `tools/llm_mapper.py`).
- Added `requirements.txt` with the core Python packages needed for Chroma, embeddings, Playwright, LangGraph, and utilities.
- Added `tools/llm_mapper.py` to map agent `model` entries to local runner endpoints.
- Added `workflows/langgraph/orchestrator_graph.py` — a minimal LangGraph orchestration example (Orchestrator → Coder → QA).
- Added `scripts/seed_chroma.py` to index markdown files from `memory/obsidian-vault` into Chroma.
- Added `scripts/setup_env.ps1` to install Python & Node dependencies and Playwright browsers on Windows.

Next recommended steps I can perform autonomously:

1. Run the `scripts/setup_env.ps1` script to install dependencies (requires internet access).
2. Run `python scripts/seed_chroma.py` to seed Chroma (requires Chroma running or appropriate client configuration).
3. Start Docker Compose services: `docker compose up -d chroma n8n prometheus grafana loki vault searxng mcp-bridge`.
4. Install and run a local LLM runner (e.g., text-generation-webui or llama.cpp HTTP bridge) so agents can use `local/llama.cpp`.

If you want, I will proceed to run `scripts/setup_env.ps1` and start the MCP bridge and Chroma services now. Confirm and I'll proceed.
