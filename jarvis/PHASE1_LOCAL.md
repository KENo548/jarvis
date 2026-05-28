# J.A.R.V.I.S. — Phase 1: Local-First Checklist

This Phase 1 checklist is tailored to the user's preference: avoid Anthropic/Gemini and paid LLM APIs. Focus on open-source, local tools.

Minimum requirements
- Windows (current), Docker Desktop, Node.js 20+, Python 3.11+
- Git
- Optional: WSL2 for Linux-like environment (recommended on Windows)

Core local services (suggested)
- Local LLM runner: `llama.cpp` or `text-generation-webui` (runs local model weights).
- Embeddings: `nomic-embed-text` or local transformer embedding implementations.
- Vector DB: `Chroma` (self-hosted local folder storage) or SQLite-backed vector store.
- Sandbox: `code-sandbox-mcp` (containerized) — run code safely in an isolated Docker network.
- Search: `SearXNG` (self-hosted) or simple Playwright scraper for targeted research.

Phase 1 tasks
1. Create `jarvis/` folder structure (agents, mcp-servers, memory, workflows, tools).
2. Create an approval queue using SQLite: a small schema with requests, status, agent, timestamp.
3. Install Docker Desktop and set up a `docker-compose.yml` to run Chroma and a local LLM runner when ready.
4. Add `git-secrets` or `gitleaks` to pre-commit hooks.
5. Create a minimal `filesystem-mcp` stub that exposes read/write capabilities to agents but requires approval for writes.
6. Add `README.md` and operational notes documenting the human-approval gate and never-commit-secrets rule.

Quick commands (examples)
Install Python deps (from repo root):
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -U pip setuptools wheel
pip install chromadb nomic-embed-text sqlite-utils
```

Create SQLite approval queue (one-off):
```powershell
python - <<'PY'
import sqlite3
db = sqlite3.connect('jarvis/memory/approval_queue.db')
db.execute('''CREATE TABLE IF NOT EXISTS approvals (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, action TEXT, payload TEXT, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
db.commit()
db.close()
print('approval queue created')
PY
```

Notes & next steps
- I can scaffold the `filesystem-mcp` and `sqlite-mcp` stubs now.
- I can also create a `docker-compose.yml` that starts Chroma and a minimal local LLM runner (if you confirm the runner choice).
- Tell me if you prefer `llama.cpp` + `text-generation-webui`, or `ggml`-based weights with `llama.cpp`, or another runner.
