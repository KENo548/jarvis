# JARVIS Fleet Commander Requirements

## Purpose

This document defines the full target state for JARVIS as a commander of a large agent fleet.

It separates two related but different goals:

- A strong AI engineering workspace with a small curated set of agents.
- A fleet-scale autonomous command infrastructure that can manage hundreds of agents from a larger library.

The first goal is already useful and realistic.
The second goal is the true long-term commander vision.

---

## Core Distinction

| Layer | Current Roadmap (Phase 1-4) | Fleet-Scale Target (Phase 5) |
| --- | --- | --- |
| Scope | AI engineering workspace | Fleet-scale autonomous command infrastructure |
| Agents | Fixed set of known core agents | Hundreds of agents from a library pool |
| Orchestration | Manual or semi-manual dispatch | Dynamic routing, discovery, and ranking |
| Memory | Task and knowledge memory | Capability memory plus organizational learning |
| Evaluation | Human review and ad hoc testing | Automated scoring, benchmarking, and trust metrics |
| Scaling | Not designed for 100+ agents | Designed for 800+ agents or more |

The roadmap is directionally correct.
It is incomplete for fleet-scale command until the missing control-plane systems are added.

---

## Current Roadmap: Phase 1 to Phase 4

### Phase 1 - Foundation

Goal: basic AI assistant with file, git, memory, and approval capabilities.

Requirements:

- Install OpenCode and connect it to an AI model.
- Set up the `C:\Jarvis` folder structure.
- Configure core MCP servers such as filesystem, GitHub, memory, SQLite, and fetch.
- Create an Obsidian vault for the knowledge base.
- Set up Bitwarden or 1Password for secrets.
- Install secret scanning such as git-secrets or Gitleaks.
- Configure Tailscale if a home server or multi-machine setup is needed.
- Test the basic loop: ask AI to write code, review the draft, and approve the commit.

Deliverable:

- Jarvis can write code, review it, and commit with your approval.

### Phase 2 - Memory and Research

Goal: persistent memory, web research, and structured planning.

Requirements:

- Install Chroma DB locally.
- Set up local embeddings such as `nomic-embed-text`.
- Add browser MCP and search MCP.
- Create a Researcher agent that can search the web and store findings.
- Set up SQLite for task history and the approval queue.
- Add a Planner agent that can read notes and create structured plans.
- Install n8n for simple automation.
- Set up Grafana and Prometheus for monitoring.

Deliverable:

- Agents can research, remember, and plan with a working knowledge base.

### Phase 3 - Multi-Agent Orchestration

Goal: full multi-agent system with safety rails, monitoring, and CI/CD.

Requirements:

- Implement a LangGraph orchestration graph connecting all agents.
- Add QA and Security agents to the pipeline.
- Set up code-sandbox MCP for safe code execution.
- Implement audit logging to an immutable append-only log.
- Add HashiCorp Vault for secrets management.
- Set up Falco for container security monitoring.
- Configure GitHub Actions for automated testing.
- Add Temporal.io for durable long-running workflows.

Deliverable:

- Jarvis becomes a multi-agent system with safety rails and CI/CD.

### Phase 4 - Advanced Capabilities

Goal: near-complete JARVIS system with knowledge graphs, voice, and self-monitoring.

Requirements:

- Add Neo4j knowledge graph support.
- Integrate Whisper for voice input.
- Deploy a cloud VPS for public-facing workflows.
- Add a Writer agent for documentation.
- Implement self-monitoring so agents can flag their own errors.
- Add a Data agent with sandboxed Python analysis.
- Explore local LLM fine-tuning as an advanced optional path.
- Run quarterly security audits.

Deliverable:

- A near-complete JARVIS system for research, code, planning, building, monitoring, and documentation.

---

## Phase 5 - Fleet Intelligence

Phase 5 is the missing commander layer.

It turns Jarvis from a useful multi-agent workspace into a true fleet-scale control plane.

### 1. Agent Registry

Critical requirement.

Jarvis needs a searchable capability database for the entire agent library.

Each agent entry should include:

- Agent name
- Canonical ID
- Specialization or domain
- Skills and subskills
- Inputs required
- Outputs produced
- Tools and MCP access
- Permissions and risk tier
- Reliability score
- Speed score
- Cost score
- Last validated version
- Deprecation status
- Dependencies
- Source location
- Tags for semantic search

Without this, the orchestrator is blind at scale.

### 2. Intelligent Routing Engine

Jarvis should not hardcode which specialist handles which task.

It should:

- Analyze the incoming task.
- Decompose it into requirements.
- Match requirements against the registry.
- Select the best-fit agent or agents.
- Route based on capability, risk, cost, and current load.
- Reroute if a specialist fails.
- Parallelize work across multiple specialists when helpful.

This is a planning and optimization problem, not just a prompt-writing problem.

### 3. Evaluation and Scoring Layer

The fleet needs a scoring system so weak agents stop getting reused automatically.

Jarvis should track:

- Task success rate
- Retry rate
- Hallucination or factual error rate
- Human approval rate
- Latency
- Token usage
- Cost per task
- Regression frequency
- Confidence score
- Benchmark history
- Domain-specific performance

This layer should support fallback selection and trust updates over time.

### 4. Agent Observability Platform

Fleet-scale management requires telemetry.

Jarvis should expose:

- Per-agent dashboards
- Cross-agent tracing
- Execution trees
- Dependency graphs
- Failure analytics
- Token usage tracking
- Cost tracking
- Bottleneck detection
- Alerting on degradation
- Historical trend views

Grafana and Prometheus help here, but Jarvis needs a true agent observability model, not just generic infra monitoring.

### 5. Agent Lifecycle Management

Agents age, drift, break, and need retirement.

Jarvis should manage:

- Version tracking per agent
- Prompt regression detection
- Tool compatibility checks
- Dependency change detection
- Validation after updates
- Retirement and deprecation workflows
- Promotion of replacement agents
- Syncing new library versions into the registry

Lifecycle management is required if the library keeps growing.

### 6. Capability Memory

Jarvis should remember what worked.

This is organizational memory for AI teams.

It should store:

- Which agents solved similar tasks successfully
- Which combinations of agents work well together
- Which tasks produce repeated failures
- Which domains each agent is strongest in
- Which agents are overused or underused
- Which routing decisions produced the best outcomes

This memory should influence future delegation.

### 7. Fleet-Level Governance

At large scale, governance matters as much as routing.

Jarvis should support:

- Workload balancing
- Priority queuing
- Rate limiting per agent or class of agent
- Cost management
- Access control by risk tier
- Approval routing by action type
- Safe fallback and escalation paths
- Separation between active, passive, and deprecated agents

### 8. Library Sync and Validation

The agent library must not be static.

Jarvis should be able to:

- Import new agent definitions
- Validate their structure
- Check required metadata
- Compare versions
- Mark agents as active or inactive
- Retire obsolete entries
- Refresh capability indexes
- Rebuild routing data when the library changes

### 9. Overload Policy

Jarvis needs an explicit policy for handling hundreds of agents.

Requirements:

- Do not try to score every agent on every task.
- Use semantic filtering before ranking.
- Limit candidate sets by domain and permission.
- Use confidence thresholds for automated selection.
- Fall back to human review when confidence is low.
- Batch low-priority work.
- Prevent runaway fan-out.

### 10. Trust Model

The commander must separate agent trust states.

Suggested states:

- Available
- Validated
- Provisionally trusted
- High confidence
- Deprecated
- Disabled

Routing and approval logic should respect trust state.

---

## Commander vs Fleet Architecture

### Commander Layer

Jarvis orchestrator should:

- Receive high-level instruction.
- Break it into subtasks.
- Decide which types of specialists are needed.
- Supervise execution.
- Assemble the final result.
- Keep the user in control for approval-sensitive actions.

The commander should not:

- Hardcode every specialist.
- Pretend to know every agent in detail.
- Directly execute risky state-changing actions without approval.

### Fleet Command Layer

This is the missing control plane between the commander and the agent pool.

Functions:

- Agent registry lookup
- Capability matching
- Routing decision
- Scoring check
- Load balancing
- Trust-state validation
- Fallback selection

### Agent Pool

The pool is the library of specialists.

It should contain:

- The active small curated fleet
- The larger specialist library
- Historical or deprecated agents
- Domain-specific variants

The commander selects from the pool instead of containing everything itself.

---

## Key Principles

1. Discovery over hardcoding - the commander should discover agents, not be manually told about every one.
2. Selection over containment - Jarvis selects specialists, it does not contain the entire library in active memory.
3. Evaluation over assumption - trust must be earned through scoring and history.
4. Observability over guesswork - you cannot manage what you cannot measure.
5. Lifecycle over static definitions - agents age and need retirement.
6. Memory-driven delegation - past success should shape future routing.
7. Safety over speed when risk is high - approval gates still matter.
8. Curated active fleet over universal activation - only load what the current task needs.

---

## Operational Recommendations (User Feedback)

The architecture is strong; the following operational adjustments are intentionally conservative and practical. They prioritize reliability, debuggability, and human control over speculative scale.

1. Reduce early emphasis on raw agent count

- Think in terms of capabilities, workflows, and reusable modules rather than a large raw agent count.
- Favor fewer, smarter, well-orchestrated specialists rather than hundreds of narrowly-scoped agents.
- Design the registry and routing to scale, but optimize for a curated active fleet by default.

2. Prefer deterministic systems where possible

- Use deterministic logic (code) for routing rules, security policies, validation, and infrastructure enforcement.
- Reserve LLMs for tasks requiring ambiguity-handling: reasoning, summarization, planning, and code generation.
- Deterministic layers reduce brittleness, make audits easier, and simplify approval gates.

3. Build observability very early

- Invest in traces, execution trees, replay systems, approval history, and token accounting from Phase 1 or 2.
- Observability enables debugging, replayable investigations, and per-agent telemetry that prevent multi-agent chaos.

4. Keep human-in-the-loop permanently

- Maintain approval gates for any high-risk state-changing actions.
- Keep agents supervised, sandboxed, and constrained; prefer supervised automation over full autonomy.
- Use human approvals as both a safety control and a source of training signal for the evaluation layer.

These adjustments should be treated as operating constraints: they shape Phase 5 design choices so the fleet is practical, debuggable, and trustworthy in real-world usage.

---

## Operating Model

### What Jarvis Should Do Now

- Manage a small active fleet well.
- Use tools, memory, approvals, and security consistently.
- Route tasks to the right specialist from the curated set.
- Maintain useful state and history.
- Keep the system stable and understandable.

### What Jarvis Should Not Pretend To Do Yet

- Automatically manage hundreds of agents without a registry.
- Infer trust and capability with no evaluation layer.
- Reliably optimize a huge fleet with no observability.
- Replace human oversight for high-risk actions.

### What Phase 5 Adds

- A real fleet intelligence layer.
- Registry, search, ranking, scoring, lifecycle, and governance.
- Dynamic routing with fallback and overload protection.
- Capability memory and trust updates.

---

## Industry Reality

As of 2026, this is the practical maturity curve:

| Level | Reality |
| --- | --- |
| Single-agent coding | Mature |
| Tool-using agents | Real |
| Small multi-agent systems | Workable |
| Autonomous coding loops | Unstable but improving |
| Large-scale agent fleets | Experimental |
| Self-improving AI organizations | Mostly research or hype |

This means the roadmap should stay ambitious without pretending the frontier is already solved.

---

## Recommended Final Roadmap

### Phase 1 - Foundation

Build the local workspace, core model connection, secrets handling, secret scanning, approval loop, and one simple coder agent.

### Phase 2 - Memory and Research

Add persistent memory, embeddings, web search, browser access, planner workflows, and monitoring basics.

### Phase 3 - Multi-Agent Orchestration

Add LangGraph, sandbox execution, audit logging, security controls, CI/CD, and durable workflows.

### Phase 4 - Advanced Capabilities

Add knowledge graphs, voice, documentation automation, self-monitoring, data workflows, and advanced infrastructure.

### Phase 5 - Fleet Intelligence

Add the commander-layer systems that make Jarvis capable of managing a large library of agents safely and efficiently.

---

## Phase 5 Success Criteria

Phase 5 is complete only when Jarvis can do the following reliably:

- Discover relevant agents from the library without manual hardcoding.
- Rank candidates using capability, trust, cost, speed, and risk.
- Route tasks to the right agent or agent group automatically.
- Re-route failures and select fallbacks intelligently.
- Track health, performance, and regressions over time.
- Retire outdated agents safely.
- Learn from prior outcomes.
- Support hundreds of agents without becoming brittle or overloaded.

---

## Stop Conditions

Do not keep adding complexity if:

- The system is already useful and stable.
- The maintenance burden starts exceeding the value.
- The fleet features are not yet being used in practice.
- Phase 1 to Phase 4 are still unstable.

The goal is leverage, not complexity.

---

## Final Truth

The current roadmap builds a strong AI engineering system.

The missing Phase 5 builds the actual fleet commander.

Jarvis should first become excellent at managing a small curated fleet.
Only after that should it evolve into a large-scale command infrastructure for the full agent library.
# JARVIS — Commander vs Fleet-Scale Requirements

## The Core Distinction

| Layer | Current Roadmap (Phase 1–4) | Fleet-Scale (Phase 5) |
|-------|-----------------------------|------------------------|
| Scope | AI engineering workspace | Fleet-scale autonomous command infrastructure |
| Agents | Fixed set (3–8 known agents) | Hundreds of agents from a library pool |
| Orchestration | Manual dispatch | Dynamic routing, discovery, ranking |
| Memory | Task/knowledge memory | Capability memory + organizational learning |
| Evaluation | Manual review | Automated scoring, benchmarking, trust metrics |
| Scaling | Not designed for 100+ agents | Designed for 800+ agents |

---

## Phase 1–4 Roadmap (Current — Foundation)

### Phase 1 — Foundation (Weeks 1–4)
- [ ] Install OpenCode and connect to AI model
- [ ] Set up `C:\Jarvis` folder structure
- [ ] Configure MCP servers: filesystem, github, memory, sqlite, fetch
- [ ] Create Obsidian vault for knowledge base
- [ ] Set up Bitwarden/1Password for secrets
- [ ] Install gitleaks for secret scanning
- [ ] Configure Tailscale VPN (optional)
- [ ] Test: ask AI to write code, review, approve commit

### Phase 2 — Memory & Research (Weeks 5–8)
- [ ] Install Chroma DB locally
- [ ] Set up nomic-embed-text for local embeddings
- [ ] Add browser-mcp (Playwright) and search-mcp (SearXNG)
- [ ] Create Researcher Agent
- [ ] Set up SQLite for task history and approval queue
- [ ] Add Planner Agent
- [ ] Install n8n for automation
- [ ] Set up Grafana + Prometheus for monitoring

### Phase 3 — Multi-Agent Orchestration (Weeks 9–14)
- [ ] Implement LangGraph orchestration graph
- [ ] Add QA Agent and Security Agent to pipeline
- [ ] Set up code-sandbox-mcp for safe execution
- [ ] Implement full audit logging
- [ ] Add HashiCorp Vault for secrets
- [ ] Set up Falco for container security
- [ ] Configure GitHub Actions for CI/CD
- [ ] Add Temporal.io for workflows

### Phase 4 — Advanced Capabilities (Weeks 15–24)
- [ ] Add Neo4j knowledge graph
- [ ] Integrate Whisper for voice input
- [ ] Deploy cloud VPS
- [ ] Add Writer Agent for documentation
- [ ] Self-monitoring: agents flag own errors
- [ ] Add Data Agent for analysis
- [ ] Explore local LLM fine-tuning
- [ ] Quarterly security audit

---

## Phase 5 — Fleet Intelligence (Missing — What Must Be Built)

### 1. Agent Registry (CRITICAL)
- Searchable capability database indexed by:
  - Agent skills / specialization
  - Reliability score
  - Cost and speed ratings
  - Tool access and dependencies
- Without this: the orchestrator is blind at scale

### 2. Intelligent Routing Engine
- Dynamically analyzes incoming tasks
- Decomposes requirements automatically
- Selects best-fit agent(s) from registry
- Reroutes on failure
- Parallelizes work across multiple specialists
- Uses optimization, not just prompts

### 3. Evaluation & Scoring Layer
- Performance tracking per agent
- Benchmark scoring
- Hallucination rate monitoring
- Task success history
- Confidence scoring
- Retry logic with fallback agents
- Bad agents stop getting reused automatically

### 4. Agent Observability Platform (beyond basic monitoring)
- Per-agent dashboards
- Cross-agent tracing
- Dependency graphs
- Execution trees
- Failure analytics
- Token usage tracking
- Bottleneck detection
- Alerting on degradation

### 5. Agent Lifecycle Management
- Version tracking per agent
- Prompt regression detection
- Tool compatibility checking
- Dependency change detection
- Retirement/deprecation workflow
- Update propagation across fleet

### 6. Capability Memory (Organizational Memory)
- Orchestrator remembers:
  - Who solved similar tasks before
  - Which agents collaborate well together
  - Failure patterns
  - Domain expertise per agent
- Becomes long-term "organizational learning" for AI teams

### 7. Fleet-Level Governance
- Workload balancing across agents
- Priority queuing
- Rate limiting per agent type
- Cost management
- Access control at fleet scale
- Approval routing by risk level

---

## Architecture: Commander vs Fleet

### The Commander (JARVIS Orchestrator — Already in Phase 1)

**Role:** Receives high-level instruction, breaks into subtasks, assigns to agents, monitors progress, assembles output.

**Does NOT:**
- Execute actions directly
- Need to know every agent's internal details

### The Fleet Command Layer (Phase 5 — Missing Today)

Adds a control plane between the commander and the agent pool:

```
User Request
       |
       v
[ Commander / Orchestrator ]
       |
       v
[ Fleet Command Layer ]          <--- NEW
  - Agent Registry Lookup
  - Capability Matching
  - Routing Decision
  - Scoring Check
  - Load Balancing
       |
       v
[ Agent Pool (800+ specialists) ]
```

---

## Key Principles for Phase 5

1. **Discovery over Hardcoding** — Orchestrator should discover agents, not be told about them
2. **Selection over Containment** — Orchestrator selects specialists, does not contain them
3. **Evaluation over Assumption** — Trust is earned through scoring, not assumed
4. **Observability over Guesswork** — You cannot manage what you cannot measure
5. **Lifecycle over Static** — Agents age, break, and need retirement
6. **Memory-Driven Delegation** — Past success informs future assignments

---

## Industry Reality (2026)

| Level | Maturity |
|-------|----------|
| Single-agent coding | Mature |
| Tool-using agents | Real |
| Small multi-agent systems | Workable |
| Autonomous coding loops | Unstable, improving |
| Large-scale agent fleets | Experimental |
| Self-improving AI orgs | Mostly research/hype |

---

## The Hard Truth

- Current roadmap gets you to: multi-agent AI engineering workspace
- Phase 5 gets you to: fleet-scale autonomous command infrastructure
- Most people building "JARVIS" today are building workflow automation with LLMs
- True fleet-scale orchestration is a distributed systems problem, not just a prompting problem

---

## Goal for C:\Jarvis Right Now

Do NOT build Phase 5 yet.

Build Phase 1 solid first. Then Phase 2. Then Phase 3.

The leap from "AI coding assistant" to "fleet-scale AI operating system" is enormous.

Current C:\Jarvis + 3–8 agents + tools + memory + approval gates is already very powerful.

Phase 5 comes only after the foundation is proven and stable.

---

*This document captures the missing fleet-scale requirements identified during review of the JARVIS AI Ecosystem Blueprint. Last updated: 2026-05-27.*
