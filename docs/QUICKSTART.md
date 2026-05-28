# JARVIS Quick Start Guide

## 10 Minutes to Your First AI-Assisted Task

### Prerequisites
- Windows 10/11, macOS, or Linux
- Node.js 20+ installed
- Python 3.11+ installed
- Git installed

---

### Step 1: Install OpenCode

Download from [opencode.ai](https://opencode.ai) and install.

---

### Step 2: Use Local-Only Models

Use the local model mapper and the bundled runner instead of cloud API keys.

1. Keep [config/user-preferences.json](/c:/jarvis/config/user-preferences.json) set to local providers.
2. Use [tools/llm_mapper.py](/c:/jarvis/tools/llm_mapper.py) to resolve model names.
3. Start your local runner or bridge before trying agent prompts.

---

### Step 3: Set Up the JARVIS Folder

```bash
# Open a terminal and navigate to where you want JARVIS to live
cd ~/Documents

# Clone or copy the jarvis folder
# (you already have it from this project)

# Run the setup script
# Windows:
powershell -ExecutionPolicy Bypass -File setup.ps1

# macOS/Linux:
chmod +x setup.sh && ./setup.sh
```

The setup script will:
- Check prerequisites
- Configure local-only defaults
- Create the directory structure
- Initialize the SQLite database
- Configure secret scanning

---

### Step 4: Configure OpenCode

1. Open OpenCode
2. Set your working folder to the `jarvis/` directory
3. Configure the local model runner or bridge in OpenCode
4. Keep `/models` pointed at your local model alias
5. MCP servers are already in `.opencode/opencode.jsonc` when you open the `jarvis` folder

---

### Step 5: Test Your Setup

In OpenCode, type:

```
List all available MCP servers and confirm they're connected.
```

Then try:

```
Read the agent definitions in the agents/ folder and summarize each agent's role.
```

---

### Step 6: Create Your Obsidian Vault

1. Download Obsidian from [obsidian.md](https://obsidian.md)
2. Open the vault at: `jarvis/memory/obsidian-vault`
3. Create a note called `Project Index.md` with your current projects

---

### Step 7: Your First Real Task

Try asking JARVIS to:

```
Search the web for the latest best practices for setting up Playwright MCP server,
then write a configuration for it in the mcp-servers/ folder.
```

---

### What's Working After Phase 1

- [x] OpenCode IDE configured with your API key
- [x] MCP servers: filesystem, github, memory, sqlite, fetch
- [x] Agent configurations deployed
- [x] Security: secret scanning, approval queue, kill switch
- [x] Obsidian vault ready
- [x] Directory structure ready to grow

### What's NOT Working Yet (Phase 2+)

- [ ] Multi-agent orchestration (LangGraph)
- [ ] Vector database (Chroma DB)
- [ ] Web search (SearXNG + browser-mcp)
- [ ] Workflow automation (n8n)
- [ ] Monitoring (Grafana + Prometheus)
- [ ] Secrets management (Vault)

Don't try to do everything at once. Let Phase 1 stabilize first.

---

### Troubleshooting

**"MCP server not found"**
```bash
python tools/approval-queue.py list
```

**"API key not configured"**
Check your local runner, `.env` file, and OpenCode settings.

**"Database connection failed"**
```bash
python tools/approval-queue.py list
```
This will create the database if it doesn't exist.

**Other issues?**
Check `logs/` for error details.
