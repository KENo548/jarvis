# JARVIS Architecture

## The Seven-Layer Model

```
┌──────────────────────────────────────────────────────┐
│  Layer 7 — Interface                                 │
│  OpenCode IDE · Claude.ai · Web UI · CLI Dashboard   │
├──────────────────────────────────────────────────────┤
│  Layer 6 — Orchestration                             │
│  LangGraph / CrewAI — Coordinates multi-agent tasks   │
├──────────────────────────────────────────────────────┤
│  Layer 5 — Agent Fleet                               │
│  Coder · Researcher · Planner · Security · QA · Writer│
├──────────────────────────────────────────────────────┤
│  Layer 4 — Tool & MCP Bus                            │
│  MCP Servers · Plugins · GitHub · Browser · APIs     │
├──────────────────────────────────────────────────────┤
│  Layer 3 — Memory & Knowledge                        │
│  Chroma DB (vectors) · SQLite (state) · Neo4j (graph)│
├──────────────────────────────────────────────────────┤
│  Layer 2 — AI Models                                 │
│  Claude (primary) · Ollama (local) · Embeddings      │
├──────────────────────────────────────────────────────┤
│  Layer 1 — Infrastructure                            │
│  Local + Cloud · Docker · Vault · Monitoring         │
└──────────────────────────────────────────────────────┘
```

## Data Flow

1. **You give an instruction** via OpenCode or the CLI
2. **Orchestrator** breaks it into subtasks
3. **Specialized agents** pick up subtasks based on their roles
4. **Tools/MCPs** execute the actual actions (files, git, search, code)
5. **Memory systems** store results (vectors in Chroma, state in SQLite)
6. **Orchestrator** assembles the final output
7. **You review and approve** before any state-changing action executes

## Human Approval Gates

```
                    ┌─────────────────┐
                    │  User Request   │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │  (decomposes)   │
                    └────────┬────────┘
                             ▼
              ┌──────────────────────────┐
              │  Specialized Agent       │
              │  (plans its approach)    │
              └────────┬─────────────────┘
                       ▼
         ┌─────────────────────────┐
         │  Action requires        │
         │  approval?              │
         └──────┬──────────┬───────┘
                │ YES      │ NO
                ▼          ▼
         ┌──────────┐  ┌──────────┐
         │ Approval │  │ Execute  │
         │  Queue   │  │ (if safe)│
         └────┬─────┘  └────┬─────┘
              │              │
         ┌────▼────┐        │
         │ You     │        │
         │ approve │        │
         └────┬────┘        │
              ▼              ▼
         ┌─────────────────────────┐
         │      Execute Action     │
         └────────┬────────────────┘
                  ▼
         ┌─────────────────┐
         │  Log + Store    │
         │  in Memory      │
         └─────────────────┘
```

## Security Boundaries

```
┌────────────────────────────────────────────────────┐
│  PUBLIC INTERNET                                    │
│  (outside world)                                    │
└──────────────┬─────────────────────────────────────┘
               │ Tailscale VPN
               ▼
┌────────────────────────────────────────────────────┐
│  JARVIS NETWORK (172.20.0.0/16)                    │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Chroma  │  │  n8n    │  │  Grafana + Loki   │  │
│  │  (8000)  │  │  (5678) │  │  (3000, 3100)     │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Vault   │  │ SearXNG  │  │     Neo4j        │  │
│  │  (8200)  │  │  (8888)  │  │  (7474, 7687)    │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  SANDBOX NETWORK (isolated, no internet)     │   │
│  │  code-sandbox-mcp runs here                  │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
               │
               ▼ (only via OpenCode on local machine)
┌────────────────────────────────────────────────────┐
│  YOUR LOCAL MACHINE                                 │
│  · OpenCode IDE                                     │
│  · Ollama (local LLM)                               │
│  · Obsidian vault                                    │
│  · Personal key storage                              │
└────────────────────────────────────────────────────┘
```
