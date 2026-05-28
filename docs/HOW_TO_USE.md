# How to Use Your Super Engineer System

## For People Who Don't Code

This folder (`jarvis/`) is your AI workshop. You talk to me (OpenCode), and I use the tools in here to do the work.

## The 3 Things You Need to Know

### 1. I Have 191 Specialist Agents

Think of them as expert contractors you can hire instantly:
- **python-pro** — Python coding expert
- **react-specialist** — Website builder
- **rust-engineer** — High-performance systems
- **security-auditor** — Finds vulnerabilities
- **database-optimizer** — Fixes slow databases
- **devops-engineer** — Sets up deployment
- **and 185 more...**

**How to use them:** Just tell me what you want to build, and I'll pick the right agent.

### 2. I Have Safety Tools (They Protect You)

| Tool | What It Does | How To Use It |
|------|-------------|--------------|
| **Approval Queue** | Stops me before I do anything risky | I'll ask "Can I do this?" — you say yes or no |
| **Kill Switch** | Emergency stop button | Run: `tools\kill-switch.ps1` in PowerShell |
| **Health Check** | Daily system checkup | Run: `tools\daily-health-check.ps1` in PowerShell |
| **Audit Log** | Records everything I do | See `logs/audit.log` |

### 3. I Need Your Approval for These Things

I'll automatically ask before:
- Writing or changing files
- Pushing code to GitHub
- Running code on your computer
- Installing anything
- Making configuration changes

I will NOT ask before:
- Reading files
- Searching the web
- Planning and suggesting ideas
- Reading documentation

## Example: Your First Conversation

**You type:** `I want to build a personal website`

**I'll do this:**
1. Pick the `frontend-developer` agent
2. Ask you what kind of site you want
3. Plan the structure
4. Show you the plan and ask: "Can I build this?"
5. You say yes
6. I build it file by file
7. You review each file
8. When done, I ask if you want to push to GitHub

## If Something Goes Wrong

**"It's doing something I don't want"**
→ Say "Stop" or "Cancel"

**"I want to start over"**
→ Say "Clear everything and start fresh"

**"Emergency — shut it all down"**
→ Open PowerShell and type:
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Admin\Documents\agency-agents-main\jarvis\tools\kill-switch.ps1
```

**Still stuck?**
→ Just ask me "I'm stuck, help" — I'll guide you step by step.
