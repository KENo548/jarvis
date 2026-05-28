# JARVIS MCP Server Setup Guide

## What is MCP?

Model Context Protocol (MCP) gives your AI agents the ability to USE tools — like hands for the AI brain. Each MCP server exposes specific capabilities that agents can call.

## Adding MCP Servers to OpenCode

OpenCode supports MCP servers natively. Add them to your OpenCode configuration.

### 1. OpenCode MCP Config Location

Find or create your OpenCode config file:
- Windows: `%APPDATA%\opencode\config.json`
- Linux: `~/.config/opencode/config.json`

### 2. MCP Server Configuration

Use the local registry in [mcp-servers/mcp-registry.json](/c:/jarvis/mcp-servers/mcp-registry.json) as the source of truth. If you want a direct OpenCode config, point it at the local packages already listed there.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\jarvis\\github-repos"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory", "--db-path", "C:\\jarvis\\memory\\sqlite\\memory.db"],
      "env": {}
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "mcp-sqlite", "--db-path", "C:\\jarvis\\memory\\sqlite\\jarvis.db"],
      "env": {}
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "mcp-fetch-server"],
      "env": {}
    },
    "browser": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp"],
      "env": {}
    },
    "search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {}
    },
    "sandbox": {
      "command": "npx",
      "args": ["-y", "code-sandbox-mcp"],
      "env": {}
    }
  }
}
```

### 3. Phase-by-Phase MCP Activation

| MCP Server | Phase | When to Enable |
|------------|-------|----------------|
| filesystem-mcp | 1 | Day 1 |
| github-mcp | 1 | Day 1 (after creating GitHub token) |
| memory-mcp | 1 | Day 1 |
| sqlite-mcp | 1 | Day 1 |
| fetch-mcp | 1 | Day 1 |
| browser-mcp | 2 | After setting up SearXNG |
| search-mcp | 2 | After setting up SearXNG |
| code-sandbox-mcp | 3 | After multi-agent system is working |
| docker-mcp | 3 | After Docker infrastructure is stable |

### 4. Testing Your MCP Setup

After configuring, test with this prompt in OpenCode:

```
List all MCP servers that are available and show me what tools each provides.
```

You should see a list of all configured servers and their available tools.

### 5. Troubleshooting

**"MCP server not found"** — The npm package may not be installed. Run:
```
npx @modelcontextprotocol/server-filesystem --help
```

**"Connection refused"** — The server may need to be started. Check the server status.

**"Permission denied"** — The server may not have access to the requested path. Check the `allowed_paths` in `mcp-servers/mcp-registry.json`.
