# JARVIS Access Control Policy

## Principle of Least Privilege

Every agent, MCP server, and human user gets only the permissions necessary for their role. If a component doesn't need access to something, it is explicitly denied.

---

## Agent Permission Matrix

| Agent | File Read | File Write | Git Push | Web Search | Code Exec | API Call | DB Write | Deploy |
|-------|-----------|------------|----------|------------|-----------|----------|----------|--------|
| Orchestrator | ALL | NO | NO | NO | NO | NO | NO | NO |
| Coder | workspace | workspace/approval | NO | NO | sandbox | NO | NO | NO |
| Researcher | documents | NO | NO | ALL | NO | GET only | NO | NO |
| Planner | workspace | workspace | NO | NO | NO | NO | NO | NO |
| Security | ALL | NO | NO | CVE only | sandbox | GET only | NO | NO |
| QA | workspace | NO | NO | NO | sandbox | NO | NO | NO |
| Writer | workspace | workspace/approval | NO | NO | NO | NO | NO | NO |
| Data | workspace | NO | NO | NO | sandbox | NO | READ only | NO |

---

## MCP Server Permission Matrix

| MCP Server | Read | Write | Execute | Network |
|------------|------|-------|---------|---------|
| filesystem-mcp | workspace | workspace/approval | NO | NO |
| github-mcp | repos | repos/approval | merge/approval | YES (GitHub only) |
| memory-mcp | ALL | ALL | NO | NO |
| browser-mcp | NO | NO | navigation | YES (restricted) |
| search-mcp | NO | NO | search | YES (SearXNG only) |
| fetch-mcp | NO | NO | GET requests | YES (whitelist) |
| sqlite-mcp | jarvis.db | jarvis.db/approval | query | NO |
| code-sandbox-mcp | NO | NO | code (sandbox) | NO |
| docker-mcp | status | containers/approval | containers/approval | jarvis-net only |

---

## Human Permission Levels

| Level | Capabilities |
|-------|-------------|
| Admin | Full system access, all approvals, config changes, security policy |
| Power User | Deploy approval, dependency approval, agent config changes |
| User | Task requests, review agent outputs, approve/reject actions |
| Observer | View dashboards, read logs, review agent activity |

---

## Implementation Requirements

1. **No shared tokens** — Every agent and service has its own credentials
2. **Credential rotation** — Every 90 days (enforced by calendar reminder)
3. **Audit trail** — All access attempts logged with timestamp, agent, action, result
4. **Quarterly review** — Permission matrix reviewed and updated every 3 months
5. **Default deny** — New agents and services start with zero permissions
