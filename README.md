# J.A.R.V.I.S. — Just A Rather Very Intelligent System

A modular, self-improving, human-supervised AI engineering ecosystem that functions like a world-class engineering team, research lab, and automation platform combined.

## Architecture

```
Interface ─► Orchestration ─► Agent Fleet ─► MCP Tools ─► Memory ─► AI Models ─► Infrastructure
(OpenCode)    (Deterministic)  (8 agents)      (10 MCPs)    (Chroma,    (Local LLMs) (Docker,
                                                           SQLite,                   Vault,
                                                           Neo4j)                   Grafana)
```

## Quick Start

```bash
# 1. Run the setup script (local-first defaults)
powershell -ExecutionPolicy Bypass -File setup.ps1

# 2. Start infrastructure services (optional for Phase 1)
cd infrastructure && docker compose up -d

# 3. Check the approval queue
python tools/approval-queue.py list

# 4. Read the quick start guide
cat docs/QUICKSTART.md
```

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/QUICKSTART.md` | Get running in 10 minutes |
| `docs/ARCHITECTURE.md` | System architecture and data flow |
| `docs/SECURITY.md` | Security framework and controls |
| `docs/MCP_SETUP.md` | MCP server configuration |
| `docs/ROADMAP.md` | Phased implementation plan |
| `docs/OPERATOR_WORKFLOW.md` | End-to-end human-in-the-loop workflow |
| `security/incident-playbook.md` | How to respond to problems |

## Key Features

- **8 Specialized Agents**: Orchestrator, Coder, Researcher, Planner, Security, QA, Writer, Data
- **10 MCP Servers**: Filesystem, GitHub, Browser, Search, Memory, SQLite, Sandbox, Fetch, Docker
- **Ironclad Security**: Zero-trust, vault, audit logging, kill switch, secret scanning, incident playbook
- **Human Supervision**: Approval gates at every state-changing action
- **Memory Systems**: Vector DB (Chroma), structured state (SQLite), knowledge graph (Neo4j)
- **Phased Growth**: Start simple, add complexity only when proven

## Project Structure

```
jarvis/
  agents/          # Agent definitions, roles, goals, prompts
  mcp-servers/     # MCP server registry and configurations
  memory/          # Chroma DB, SQLite, Obsidian vault
  workflows/       # n8n exports, LangGraph graphs
  tools/           # Approval queue, kill switch, safety loop
  infrastructure/  # Docker Compose, env templates, monitoring
  security/        # Vault config, policies, incident playbook
  logs/            # Audit logs, agent logs, error logs
  docs/            # All system documentation
```

## License

This project is open source. Use it, modify it, improve it.
