# Data Minimization Policy

Agents only access data they need. Sensitive personal data is not stored in vector databases unless necessary.

## Principles

1. **Least privilege data access**: Each agent requests only the data required for its current task.
2. **No bulk ingestion**: Agents do not dump entire files or databases into Chroma/Neo4j without explicit approval.
3. **Retention limits**: Agent memory expires after 90 days unless explicitly preserved.
4. **Sensitive data boundaries**: PII, API keys, and credentials are never stored in vector databases.

## Agent Data Access Matrix

| Agent | Can Access | Cannot Access |
|-------|-----------|---------------|
| Coder | Source code, git history, test results | API keys, user data, other agents' memory |
| Researcher | Web content, documentation, search results | Internal code, credentials, other agents' outputs |
| Planner | Obsidian vault, project docs, task history | Source code, API keys, credentials |
| Security | Audit logs, dependency lists, config files | User data, API keys (except for scanning) |
| QA | Test results, code diffs, CI logs | API keys, user data, other agents' memory |
| Writer | Documentation, changelogs, project structure | Source code, API keys, credentials |
| Data | Database schemas, query results | API keys, credentials, other agents' memory |

## Vector Database Rules

- **Chroma**: Store only agent-relevant context (code snippets, research findings, plans). Never store raw API responses containing credentials.
- **Neo4j**: Store project relationships and code structure. Never store secrets or credentials as graph properties.
- **SQLite**: Store operational state (approvals, kill switch, metrics). Credentials go in the OS keyring, not SQLite.

## Enforced by

- `security/access-control-policy.md` — defines per-agent permissions
- `mcp-servers/mcp-registry.json` — defines per-MCP-server blocked paths
- `tools/action_whitelist.py` — runtime enforcement of allowed actions
