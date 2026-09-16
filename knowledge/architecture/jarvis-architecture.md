# JARVIS Architecture

## Overview

JARVIS is an OpenCode-native orchestration system that coordinates specialist AI agents to accomplish complex software engineering objectives.

## Core Components

### 8 Core Agents
- **jarvis-planner** — Mission decomposition and planning
- **jarvis-orchestrator** — Execution flow control
- **jarvis-engineer** — Code implementation
- **jarvis-researcher** — Investigation and research
- **jarvis-reviewer** — Independent quality review
- **jarvis-qa** — Testing and verification
- **jarvis-oversight** — Background supervision
- **jarvis-web** — Web automation

### 24 Specialist Skills
On-demand knowledge loaded via the `skill` tool when specific expertise is needed.

### 3 MCP Servers
- **memory** — Persistent memory across sessions
- **docker** — Container management
- **sqlite** — Direct database queries

### Configuration
- **projects.json** — Project registry with cross-platform paths
- **capabilities.json** — Semantic skill routing
- **security-policy.json** — Approval rules and protected paths
- **orchestration.md** — Concurrency and delegation rules

## Delegation Model

```
User → Commander (jarvis.md)
         ├── Planner → Plan
         ├── Orchestrator → Execute Plan
         │     ├── Engineer → Implement
         │     ├── Researcher → Investigate
         │     └── Web → Browser Automation
         ├── Reviewer → Quality Gate
         ├── QA → Verification
         └── Oversight → Monitor
```

## Sync Model

**GitHub as the only synchronization layer:**

```
PC → commit → push → GitHub → pull → Oracle
Oracle → commit → push → GitHub → pull → PC
```

No automatic filesystem sync. Git is source of truth.

## Security Model

- Protected paths: agents, instructions, security config, orchestration config
- JARVIS may inspect protected paths autonomously
- Material modifications require user approval
- Self-improvement must never weaken security boundaries

## Resource Constraints

- Oracle VM: 1 OCPU, 6GB RAM
- Max parallel subagents: 3
- Max delegation depth: 2
- Memory ceiling: 4.5GB (leaves 1.5GB for OS)

## Model Evaluation / Routing Policy

Configuration decision applied 2026-09-16. All agents run on frontier/default models (`model:` field absent) for production.

### Free-model bake-off (completed)

A controlled bake-off of free-tier models (muse, mimo, ling, ultra, lightning) was completed across instruction adherence, defect detection, oversight, engineering, agentic tool-use, and artifact-integrity tests.

### Durable conclusions

- **Tested free models are PUBLIC/SYNTHETIC only** under current data policy.
- **No free model is approved for private-source production roles.**
- **Frontier/default models remain the production default** for all agents.
- **Capability winner does not imply data-sensitivity authorization** — routing decisions must be made independently on capability and data policy.
- **Evaluator-error vs model-error principle**: when an evaluating agent's answer key or rubric is faulty, models that correctly reject it receive credit; a model failing on a faulty key is not evidence of model error.
- **Free-model availability is temporary/dynamic** (catalog churn, retired models, rate limits) and must not become a hard architectural dependency.

### Future routing dimensions (documented, not implemented)

ROLE + COMPLEXITY + DATA SENSITIVITY + AVAILABILITY + COST

No dynamic routing is active. Static frontier defaults remain the production configuration; any future free-model tier must be explicitly scoped to public/synthetic-only work and re-validated before adoption.
