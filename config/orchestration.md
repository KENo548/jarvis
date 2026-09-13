# Orchestration Rules

## Platform-Aware Concurrency

JARVIS operates on multiple platforms with different resource profiles. Commander must detect the current platform and apply appropriate limits.

### Load Platform Profile

Commander determines which profile to use:
1. Check `config/profiles/windows.json` if on Windows
2. Check `config/profiles/oracle.json` if on Linux ARM64
3. Fall back to conservative defaults if detection fails

### Concurrency Limits by Profile

| Dimension | Oracle (ARM64) | Windows PC | Rationale |
|-----------|---------------|------------|-----------|
| Max parallel subagents | 3 | 4 | Reasoning parallelism (remote API) has no local cost |
| Max delegation depth | 2 | 3 | PC can handle deeper coordination chains |
| Max concurrent file edits | 1 | 2 | Prevents write conflicts |
| Max concurrent bash commands | 2 | 4 | PC has more CPU threads |
| Memory ceiling | 4.5GB | 6.0GB | Leaves headroom for OS + OpenCode runtime |

### Platform-Specific Capabilities

| Capability | Oracle | Windows PC |
|-----------|--------|------------|
| Desktop automation | No | Yes (optional) |
| Voice I/O | No | Yes (optional) |
| Browser automation | Yes | Yes |
| PowerShell tools | No | Yes (primary) |
| Bash tools | Yes (primary) | Yes (via WSL) |
| Local services | Yes | Yes |

## Resource-Awareness

- **Reasoning parallelism** (remote LLM API): No local cost — can dispatch 2-4 remote tasks depending on platform
- **Tool parallelism** (local file/ bash ops): Limited by platform profile
- Don't dispatch tool-heavy subagents in parallel with each other on constrained platforms
- Serialize when tasks touch the same resources
- On Windows PC: prefer PowerShell tools over bash for native reliability
- On Oracle: use bash tools exclusively

## Orchestration Patterns

### Pattern 1: Sequential (simple tasks)
```
User → Commander → [single specialist] → result
```

### Pattern 2: Fan-out (medium tasks)
```
User → Commander → Orchestrator → [N parallel specialists] → merge → Commander → user
```
N = platform.max_parallel_subagents

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

## Cross-Platform Compatibility

The orchestration rules are shared across platforms. Platform-specific behavior is determined by:
- `config/profiles/windows.json` — Windows PC capabilities and limits
- `config/profiles/oracle.json` — Oracle VM capabilities and limits
- Commander detects platform at runtime and applies the correct profile

Platform-specific tools must never become requirements for the portable core.
A capability committed to the shared repository may be marked `platforms: ["windows"]`
without causing Oracle to load, execute, or depend on it.
