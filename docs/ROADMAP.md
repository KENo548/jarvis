# JARVIS Implementation Roadmap

## Overview

Build a fully autonomous, modular, self-improving AI engineering ecosystem. Each phase produces a working, useful system before adding the next layer.

```
Phase 1 ─► Foundation (Weeks 1-4)
Phase 2 ─► Memory & Research (Weeks 5-8)
Phase 3 ─► Multi-Agent Orchestration (Weeks 9-14)
Phase 4 ─► Advanced Capabilities (Weeks 15-24)
```

The ecosystem is built on a **Seven-Layer Architecture**: Infrastructure → AI Models → Memory & Knowledge → Tool & MCP Bus → Agent Fleet → Orchestration → Interface.

---

## The Five Pillars

| Pillar | What It Means |
|--------|---------------|
| **Modularity** | Each component is independent — swap, upgrade, or remove it without breaking everything else. |
| **Human Oversight** | The system proposes, you approve. No autonomous deployments, code execution, or web actions without your sign-off. |
| **Security First** | Every layer is hardened. Zero-trust networking, secrets management, audit logs, and intrusion detection built in from day one. |
| **Open Source Priority** | Prefer open, auditable tools. Avoid vendor lock-in. Own your data and your stack. |
| **Phased Growth** | Start simple and stable. Add complexity only when the foundation is proven. Never chase hype. |

---

## The Seven-Layer Architecture

| Layer | Description |
|-------|-------------|
| **Layer 7 — Interface** | OpenCode IDE, Claude.ai, Web UI, CLI dashboard. Where you interact. |
| **Layer 6 — Orchestration** | LangGraph / CrewAI agent graphs. Coordinates multi-agent tasks. |
| **Layer 5 — Agent Fleet** | Specialized AI agents: Orchestrator, Coder, Researcher, Planner, Security, QA, Writer, Data. |
| **Layer 4 — Tool & MCP Bus** | MCP servers, plugins, GitHub, browser, file system, APIs. |
| **Layer 3 — Memory & Knowledge** | Vector DB (Chroma), graph store (Neo4j), SQL state (SQLite), long-term memory, session cache (Redis). |
| **Layer 2 — AI Models** | Claude (primary), local LLMs via Ollama (fallback/privacy), embeddings. |
| **Layer 1 — Infrastructure** | Local machine + cloud VPS, Docker containers, secrets vault, monitoring stack. |

---

## Data Flow

You give an instruction → Orchestrator breaks it into subtasks → Agents pick up subtasks → Tools/MCPs execute actions → Memory stores results → Orchestrator assembles output → You review & approve → done.

**Human Approval Checkpoints**
- Any code execution on production systems
- Any outbound API calls that create, update, or delete data
- Dependency installs or version upgrades
- GitHub pushes, PRs, or releases
- Any scheduled or autonomous background tasks (require explicit whitelist)

---

## Phase 1: Foundation (Weeks 1–4)

**Goal**: Basic AI coding assistant with file, git, memory, and security capabilities.

- [x] Install OpenCode IDE — local-first with Ollama (no paid API keys)
- [x] Install Ollama (LLaMA 3 / Mistral) for local LLM and privacy-sensitive tasks — `tools/setup-ollama.ps1`
- [x] Install Node.js 20+, Python 3.11+, and Docker Desktop — verified via `tools/check-prerequisites.ps1`
- [x] Set up `jarvis/` folder structure
- [x] Configure core MCP servers: filesystem, github, memory, fetch
- [x] Create Obsidian vault for personal knowledge base and link it to agent context
- [x] First agent: Coder Agent — can read/write files and commit to GitHub with your approval
- [x] Test: Ask AI to write code, review draft, approve commit

### Phase 1 — Security Implementation

- [x] Set up free-tier secrets management via OS keyring (Windows Credential Locker / macOS Keychain / Linux Secret Service) — `tools/secrets_client.py`
- [x] Install git-secrets and gitleaks for secret scanning — CI pipeline + `tools/git-secrets-setup.ps1`
- [x] Enable SSH key authentication (Ed25519) and disable password login — `tools/setup-ssh.sh`
- [ ] Enable multi-factor authentication on GitHub (manual — enable in GitHub Settings > Password and authentication > Two-factor authentication)
- [x] Configure UFW firewall: default deny, allow SSH and VPN only — `tools/setup-firewall.sh`
- [x] Configure Tailscale VPN (free tier, 100 devices) — `tools/setup-tailscale.sh`
- [x] Set up cron + shell scripts for scheduled tasks — `tools/daily-health-check.ps1`
- [x] Define Principle of Least Privilege — `security/access-control-policy.md`
- [x] Enforce: never commit API keys, passwords, or private keys — gitleaks in CI + `.gitignore` blocklist
- [x] Encrypt local disks containing sensitive data — `docs/DISK_ENCRYPTION.md`

**Deliverable**: You can ask JARVIS to write code, review it, and commit to GitHub with your approval. Security foundation is live.

**Cost**: $0/month (local LLM via Ollama, free-tier tools only)

---

## Phase 2: Memory & Research (Weeks 5–8)

**Goal**: Persistent memory, web research, structured planning, and operational safety.

- [x] Install Chroma DB locally (via Docker)
- [x] Set up nomic-embed-text for local embeddings
- [x] Add Redis for session caching — `docker-compose.yml` (redis:7-alpine, AOF persistence)
- [x] Add browser-mcp (Playwright) and search-mcp (SearXNG)
- [x] Add docker-mcp and calendar-mcp — both in `mcp-registry.json`
- [x] Configure sqlite-mcp and set up SQLite for task history and approval queue
- [x] Create Researcher Agent — can search the web and store findings in Chroma
- [x] Create Planner Agent — reads Obsidian notes and creates structured plans
- [x] Install n8n for simple automation
- [x] Set up Grafana + Prometheus for monitoring and Loki for log aggregation

### Phase 2 — Security Implementation

- [x] Implement approval queue: all state-modifying agent actions require your sign-off — `tools/approval-queue.py`
- [x] Define action whitelist: read/search/test = auto-allowed; everything else requires approval — `tools/action_whitelist.py` + `security/action-whitelist.json`
- [x] Implement output validation: code in sandbox, SQL syntax-checked, API calls dry-run preview — `tools/output_validator.py`
- [x] Configure rate limiting on all APIs — `tools/rate_limiter.py` (token bucket, per-agent)
- [x] Implement 3-2-1 backup strategy (Restic + Backblaze B2) — `tools/backup.sh`
- [x] Encrypt Chroma DB folder and SQLite files at rest — `docs/DISK_ENCRYPTION.md` (LUKS/FileVault/BitLocker guide)
- [x] Apply data minimization: agents only access data they need — `security/data-minimization.md` + agent access matrix
- [x] HTTPS with Let's Encrypt — `infrastructure/nginx/README.md` (nginx reverse proxy + certbot config)

**Deliverable**: Agents can research, remember, and plan. You have a working knowledge base with safety rails and monitoring.

**Cost**: $0/month (all local, free-tier tools)

---

## Phase 3: Multi-Agent Orchestration (Weeks 9–14)

**Goal**: Full multi-agent system with deterministic orchestration, safety rails, monitoring, and CI/CD.

- [ ] Implement LangGraph orchestration graph connecting all agents (CrewAI and AutoGen available for specialized team workflows)
- [ ] Add Orchestrator Agent — receives high-level instructions, breaks into subtasks, assigns to agents, monitors progress, assembles final output
- [ ] Add QA Agent and Security Agent to the pipeline
- [ ] Set up code-sandbox-mcp for safe code execution in isolated Docker networks with no internet access by default
- [ ] Configure GitHub Actions for automated testing on every commit
- [ ] Add Temporal.io for durable long-running workflows (optional; not yet wired)

### Phase 3 — Security Implementation

- [ ] Implement full audit logging to immutable append-only log files (timestamp, agent ID, action type, inputs, outputs, approval status)
- [ ] Add HashiCorp Vault for centralized secrets management — agents request secrets at runtime, never store in code or config
- [ ] Set up Falco for real-time container security monitoring
- [ ] Implement zero-trust networking with mTLS between services
- [ ] Add prompt injection defense: sanitize all external content (web scraping, file contents, user inputs) before passing to LLMs
- [ ] Implement kill switch: single flag in SQLite stops all agents immediately; agents check this flag before every action
- [ ] Deploy Security Agent audits: dependency CVE checks, log anomaly detection, policy validation
- [ ] Set up Fail2Ban to automatically ban IPs showing brute-force attack signs against SSH or web interfaces
- [ ] Maintain isolated sandbox networks: AI code execution happens in Docker networks isolated from real systems; no internet access from sandbox by default

**Deliverable**: Full multi-agent system with deterministic orchestration, safety rails, monitoring, and CI/CD.

**Cost**: ~$50-80/month (adds VPS for Temporal ~$10-20/month)

---

## Phase 4: Advanced Capabilities (Weeks 15–24)

**Goal**: Near-complete JARVIS system with knowledge graphs, voice, self-monitoring, and advanced analytics.

- [ ] Add Neo4j knowledge graph — map relationships between projects, tools, people, and code
- [ ] Integrate Whisper for voice input to agents
- [ ] Deploy cloud VPS for public-facing workflows and always-on automation
- [ ] Add Writer Agent for automatic documentation generation (READMEs, changelogs, reports)
- [ ] Add Data Agent with sandboxed Python for analysis, reporting, and chart generation
- [ ] Implement self-monitoring: agents flag their own errors and request help
- [ ] Integrate GPT-4o for vision tasks and structured outputs if Claude coverage gaps exist (optional)
- [ ] Explore local LLM fine-tuning for domain-specific tasks (advanced, optional)

### Phase 4 — Security Implementation

- [ ] Quarterly security audit: rotate all API keys (90-day cycle), review permissions, test backups, practice incident playbook
- [ ] Document and maintain incident response playbook: agent misbehavior, credential leaks, service compromise
- [ ] Review and update the action whitelist, approval queue rules, and kill switch procedures

**Deliverable**: A near-complete JARVIS system. Research, code, plan, build, monitor, document — all in one.

**Cost**: ~$70-120/month (adds Neo4j hosting, VPS upgrades)

---

## Agent Fleet

Each agent is a specialized AI with a defined role, a set of tools, and clear boundaries. Specialization makes agents more reliable and easier to audit.

| Agent | Role & Access |
|-------|---------------|
| **Orchestrator** | The general. Receives your high-level instruction, breaks it into subtasks, assigns to agents, monitors progress, assembles final output. Does not execute actions directly. |
| **Coder Agent** | Writes, reviews, tests, and refactors code. Has access to filesystem-mcp, github-mcp, code-sandbox-mcp. Cannot push to production without approval. |
| **Researcher Agent** | Searches the web, reads documentation, summarizes findings, checks for new tools and security vulnerabilities. Has access to browser-mcp, search-mcp, fetch-mcp. |
| **Planner Agent** | Breaks complex goals into step-by-step plans with dependencies, time estimates, and risk flags. Creates project structures in Obsidian. |
| **Security Agent** | Audits code for vulnerabilities, checks dependency CVEs, monitors logs for anomalies, validates agent actions against security policy. |
| **QA Agent** | Writes and runs tests, validates outputs, compares before/after states, flags regressions. Always runs before Coder Agent pushes code. |
| **Writer Agent** | Drafts documentation, READMEs, changelogs, reports, and emails. Has access to filesystem-mcp only. |
| **Data Agent** | Queries databases, builds reports, analyzes CSVs, generates charts. Has access to sqlite-mcp and a sandboxed Python environment. |

---

## Local + Cloud Hybrid Setup

| Location | What Lives There |
|----------|------------------|
| **Your Local Machine** | OpenCode IDE, Ollama (local LLM), Obsidian vault, personal key storage, Tailscale client. |
| **Home Server / NAS (optional)** | Chroma DB, n8n, monitoring stack (Grafana/Prometheus/Loki), backups. Always-on, low power. |
| **Cloud VPS (Hetzner / Fly.io)** | Public-facing services, GitHub Actions runners, Temporal.io, SearXNG search. ~$5–20/month. |
| **Cloud Storage (Backblaze B2)** | Encrypted backups only. $0.006/GB/month — cheapest reliable option. Never store unencrypted data. |
| **Anthropic API** | Claude for primary reasoning. API calls from your local machine or VPS, never from untrusted environments. |

**Beginner Recommendation**: Start with just your local machine and the Anthropic API. Add a home server in Phase 2 and cloud VPS in Phase 3.

**Total Phase 1 cost**: Your existing hardware + Anthropic API usage (~$20–50/month depending on use).

---

## Never Do These Things

**Hard Rules — No Exceptions**

- [ ] Never put API keys or passwords in code files or git repositories
- [ ] Never give an agent production database write access without an approval gate
- [ ] Never run agent-generated code on your main machine without sandbox testing first
- [ ] Never skip the security agent step before deploying code
- [ ] Never use the same API key for development and production
- [ ] Never expose services to the public internet without authentication and rate limiting
- [ ] Never let the system update its own dependencies without your explicit approval

---

## Recommended Learning Resources

- [ ] LangGraph documentation: langchain-ai.github.io/langgraph
- [ ] Model Context Protocol: modelcontextprotocol.io
- [ ] HashiCorp Vault getting started: developer.hashicorp.com/vault
- [ ] Tailscale documentation: tailscale.com/kb
- [ ] Grafana getting started: grafana.com/docs/grafana/latest/getting-started
- [ ] n8n self-hosting guide: docs.n8n.io/hosting

---

## Dependency & Version Management

### Rules
- [ ] Pin all dependencies to exact versions in your config files. Never use `latest` in production.
- [ ] Use Renovate Bot (free, open source) to automatically open PRs for dependency updates. Review before merging.
- [ ] Run Dependabot on all GitHub repositories. It flags security vulnerabilities in dependencies automatically.
- [ ] Before upgrading any dependency, run your full test suite in the sandbox environment first.
- [ ] Keep a changelog. Every upgrade is documented with the version, date, and reason.
- [ ] Use Docker for all services — container images lock dependency versions perfectly.

### The Safety Loop for Updates
1. Renovate Bot opens a PR with the proposed update
2. Security Agent reviews the changelog for breaking changes or CVEs
3. QA Agent runs tests in the sandbox environment
4. You review the QA report and approve or reject the PR
5. If approved, GitHub Actions deploys the update and monitors for errors
6. If errors appear within 24 hours, automated rollback to previous version

---

## Ironclad Security Framework

Security is not optional. An autonomous AI system with access to your files, code, GitHub, and APIs is a high-value target. The checklist items above are implemented phase-by-phase; this section provides the complete reference framework.

### Identity & Access Management
- **Principle of Least Privilege**: Every agent and MCP server gets only the permissions it needs. The researcher agent cannot write code. The coder agent cannot push to production.
- **API Key Rotation**: Rotate all API keys every 90 days. Use a password manager (Bitwarden, 1Password). Never reuse keys across services.
- **HashiCorp Vault**: Centralized secrets management. Agents request secrets at runtime — secrets are never stored in code or config files.
- **Multi-Factor Authentication**: Enable MFA on GitHub, cloud providers, and any service with admin access. Use an authenticator app, not SMS.
- **SSH Key Authentication**: Disable password login on all servers. Use Ed25519 SSH keys. Store private keys only on your local machine.

### Network Security
- **Zero-Trust Networking**: Every service authenticates every request. Nothing is trusted just because it's on the same machine. Use mTLS between services.
- **Tailscale VPN**: Private mesh network for all your machines. Access your home server from anywhere without exposing ports. Free tier is generous.
- **Firewall Rules**: Block all inbound ports except SSH (22) and your VPN. Use UFW (Linux) or a cloud security group. Default: deny all, allow explicitly.
- **Rate Limiting**: All APIs and web interfaces must have rate limiting. Prevents brute force and runaway agents from hammering services.
- **Isolated Sandbox Networks**: AI code execution must happen in a Docker network isolated from your real systems. No internet access from the sandbox by default.

### Data Protection
- **Encryption at Rest**: Encrypt all disks containing sensitive data (LUKS on Linux, FileVault on Mac). Encrypt the Chroma DB folder and SQLite files.
- **Encryption in Transit**: All HTTP traffic uses HTTPS. Use Let's Encrypt for free TLS certificates. Never transmit secrets over plain HTTP.
- **Backup Strategy (3-2-1)**: 3 copies, 2 different media types, 1 offsite. Use Restic + Backblaze B2 for automated encrypted backups. Test restores monthly.
- **Data Minimization**: Don't give agents access to data they don't need. Don't store sensitive personal data in vector databases unless necessary.
- **Secret Scanning**: Install git-secrets or Gitleaks. Block commits that contain API keys, passwords, or private keys.

### Agent Safety Controls
- **Approval Queue**: All agent actions that modify state go into a queue. You see a summary: what the agent wants to do, why, and the estimated impact. You approve or reject.
- **Action Whitelist**: Maintain an explicit list of actions agents can take without approval: read files, search the web, run tests in sandbox. Everything else requires approval.
- **Output Validation**: All agent outputs are validated before use. Code is run in sandbox first. SQL queries are syntax-checked. API calls are previewed as dry-runs.
- **Prompt Injection Defense**: Agents should never pass unvalidated external content directly into prompts. Sanitize web scraping results, file contents, and user inputs before passing to LLMs.
- **Kill Switch**: A single command must be able to stop all agents immediately. Implement as a flag in SQLite: agents check this flag before every action.
- **Audit Log**: Every agent action is logged with timestamp, agent ID, action type, inputs, outputs, and whether it was approved or auto-executed. Immutable, append-only log.

### Monitoring & Incident Response
- **Grafana + Prometheus**: Real-time dashboards for system health, API usage, error rates, agent activity. Set alerts for anomalous behavior.
- **Loki (log aggregation)**: Centralized log collection from all containers. Search across all logs in one place. Part of the Grafana stack.
- **Falco (container security)**: Detects suspicious behavior inside Docker containers in real time. Alerts if a container tries to access files or network it shouldn't.
- **Fail2Ban**: Automatically bans IPs that show signs of brute-force attacks against SSH or web interfaces.
- **Incident Playbook**: Document what to do if an agent misbehaves, if credentials are leaked, or if a service is compromised. Practice the playbook quarterly.

---

## Principles

1. **Don't skip phases** — Each phase builds on the previous one
2. **Stabilize before advancing** — If a phase feels shaky, don't move on
3. **Test everything** — Every component should be verified before depending on it
4. **Security from day one** — Not added later, built into every phase
5. **You stay in control** — The system proposes, you approve

---

## When to Stop

- You have a working system that meets your needs
- The complexity is adding more overhead than value
- You're spending more time maintaining than using
- The system is stable and predictable

The goal is leverage, not complexity. Stop when the system makes you dramatically more capable without becoming a burden to maintain.
