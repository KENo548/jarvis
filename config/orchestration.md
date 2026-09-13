# Orchestration Rules

## Concurrency Limits

| Dimension | Limit | Rationale |
|-----------|-------|-----------|
| Max parallel subagents | 3 | Remote reasoning cheap; local tool calls serialized |
| Max delegation depth | 2 | Commander → Team Lead → Specialist |
| Max concurrent file edits | 1 | Prevents write conflicts |
| Max concurrent bash commands | 2 | Limited by 1 OCPU |
| Memory ceiling | 4.5GB | Leaves 1.5GB for OS + OpenCode runtime |

## Orchestration Patterns

### Pattern 1: Sequential (simple tasks)
```
User → Commander → [single specialist] → result
```

### Pattern 2: Fan-out (medium tasks)
```
User → Commander → Orchestrator → [3 parallel specialists] → merge → Commander → user
```

### Pattern 3: Pipeline (complex tasks)
```
User → Commander → Planner → [Plan]
                        ↓
                   Orchestrator → [Engineer + Researcher parallel]
                        ↓
                   Reviewer → [feedback]
                        ↓
                   Commander → [if approved: ship; if rejected: loop]
```

### Pattern 4: Investigative (debugging)
```
User → Commander → Researcher → [investigation]
                        ↓
                   Planner → [fix plan]
                        ↓
                   Engineer → [implementation]
                        ↓
                   QA → [verification]
```

## Resource-Awareness

- **Reasoning parallelism** (remote LLM API): No local cost — can dispatch 2-3 remote tasks
- **Tool parallelism** (local bash/file ops): Limited by 1 OCPU + 6GB RAM
- Don't dispatch tool-heavy subagents in parallel with each other
- Serialize when tasks touch the same resources

## Conflict Resolution

When agents produce conflicting results:
1. Preserve both outputs
2. Identify the conflict
3. Evaluate evidence
4. Escalate if architectural
5. Merge if possible

## Failure Handling

```
Task FAILED → Preserve output → Diagnose cause → Reassign/Retry → Report
```

Do not restart blindly. Build on what was learned.

---
*Source: C:\Jarvis\.opencode\skills\jarvis-orchestration\SKILL.md*
