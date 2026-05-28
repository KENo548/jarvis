# JARVIS Operator Workflow

How to use JARVIS end-to-end: ask → review → approve → commit.

## The Loop

```
You ask ──► Orchestrator routes ──► Agent works ──► Approval queue ──► You review ──► Approve/Reject ──► Done
```

Every state-changing action follows this loop. Read-only actions (web search, file reads) skip the approval step.

---

## Step-by-Step: Your First Task

### 1. Ask JARVIS

In OpenCode, type a task. Examples:

```
Write a Python script to fetch exchange rates from an API and cache them in SQLite.
```

```
Research the best practices for securing a self-hosted n8n instance.
```

### 2. Orchestrator Routes

The orchestration graph (`tools/orchestration_graph.py`) inspects your task and routes it to the right agent:

| If task mentions... | Agent |
|---------------------|-------|
| `code`, `implement`, `bug`, `refactor`, `test` | Coder (with sandbox validation) |
| `research`, `search`, `documentation`, `docs` | Researcher (with web search) |
| `plan`, `roadmap`, `design`, `architecture` | Planner (with Obsidian context) |
| `security`, `audit`, `vulnerability` | Security |
| `qa`, `test`, `verify` | QA |

### 3. Agent Works

The agent picks up the subtask, uses its assigned MCP tools, and produces output. The sandbox runner isolates any code execution.

### 4. Approval Queue Pops

A new entry appears in the queue:

```powershell
python tools/approval-queue.py list
```

Output:
```
ID: abc123 | Agent: coder | Action: write file | Risk: medium
Proposed: src/exchange_rates.py
```

### 5. You Review

Read what the agent wants to do:

```powershell
python tools/approval-queue.py show abc123
```

Check the proposed file, the risk level, and the agent's reasoning.

### 6. Approve or Reject

```powershell
# Approve
python tools/approval-queue.py approve abc123

# Reject with reason
python tools/approval-queue.py reject abc123 "Use httpx instead of requests"
```

If rejected, the agent revises and re-queues.

### 7. Done

The approved action executes. The result is logged to `logs/audit.log`.

---

## Daily Operations

### Morning: Run Health Check

```powershell
powershell -ExecutionPolicy Bypass -File tools/daily-health-check.ps1
```

Verifies: databases, Docker services, disk space, gitleaks hook, secrets safety.

### Before Any Commit

Gitleaks scans automatically via pre-commit hook. If a secret is detected, the commit is blocked.

### Emergency: Kill Switch

```powershell
powershell -ExecutionPolicy Bypass -File tools/kill-switch.ps1
```

Stops all agent actions immediately. Reset with:

```powershell
python tools/reset-kill-switch.py
```

---

## Phase 1 Deliverable

Per the blueprint: **"You can ask an AI to write code, review it, and commit to GitHub with your approval."**

The flow is:
1. Ask JARVIS to write code
2. Orchestrator routes to Coder Agent
3. Coder produces code in sandbox
4. Approval queue pops — you review the diff
5. You approve or reject
6. If approved, code is written to disk
7. You `git add` + `git commit` (gitleaks scans automatically)
8. You `git push` when ready

All local. All under your control.
