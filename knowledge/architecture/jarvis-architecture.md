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
