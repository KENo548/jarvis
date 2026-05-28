# JARVIS Security Framework

## Ironclad Security: Not Optional

An autonomous AI system with access to your files, code, GitHub, and APIs is a high-value target. Every control listed here is required — not optional.

## Layer 1: Identity & Access Management

| Control | Implementation |
|---------|---------------|
| Principle of Least Privilege | Agents get only the permissions they need. Permission matrix in `security/access-control-policy.md` |
| API Key Rotation | Rotate every 90 days. Use Bitwarden. Never reuse keys. |
| HashiCorp Vault | Centralized secrets. Agents request secrets at runtime — never stored in code. |
| Multi-Factor Authentication | MFA on GitHub, cloud providers, and admin services. Authenticator app, not SMS. |
| SSH Key Authentication | Ed25519 keys only. Password login disabled everywhere. |

## Layer 2: Network Security

| Control | Implementation |
|---------|---------------|
| Zero-Trust Networking | Every service authenticates every request. Nothing trusted by network position. |
| Tailscale VPN | Private mesh network for all machines. Free tier supports 100 devices. |
| Firewall Rules | Default deny all inbound. Allow only SSH (22) and VPN explicitly. |
| Rate Limiting | All APIs and web interfaces. Prevents brute force and runaway agents. |
| Isolated Sandbox | Docker network isolated from real systems. No internet by default. |

## Layer 3: Data Protection

| Control | Implementation |
|---------|---------------|
| Encryption at Rest | Full-disk encryption (BitLocker/FileVault/LUKS). Encrypted Chroma DB folder. |
| Encryption in Transit | HTTPS everywhere. Let's Encrypt TLS. Never plain HTTP for secrets. |
| 3-2-1 Backup Strategy | 3 copies, 2 media types, 1 offsite. Restic + Backblaze B2. Test monthly. |
| Data Minimization | Only necessary data. No personal data in vector DBs. |
| Secret Scanning | gitleaks pre-commit hooks. Blocks commits with keys, passwords, or secrets. |

## Layer 4: Agent Safety Controls

| Control | Implementation |
|---------|---------------|
| Approval Queue | All state-changing actions queue for human review. `tools/approval-queue.py` |
| Action Whitelist | Explicit list of auto-approvable actions. Everything else requires approval. |
| Output Validation | Code runs in sandbox first. SQL syntax-checked. API calls dry-run previewed. |
| Prompt Injection Defense | External content sanitized before passing to LLMs. No raw web scraping into prompts. |
| Kill Switch | Single command stops all agents. `tools/kill-switch.ps1` or `tools/kill-switch.sh` |
| Audit Log | Immutable, append-only log of every action. `logs/audit.log` |

## Layer 5: Monitoring & Incident Response

| Tool | Role |
|------|------|
| Grafana + Prometheus | Real-time dashboards. System health, API usage, error rates, agent activity. |
| Loki | Centralized log collection from all containers. |
| Falco | Container security. Detects suspicious behavior in Docker. |
| Fail2Ban | Auto-bans brute-force IPs against SSH and web interfaces. |
| Incident Playbook | Documented response procedures. `security/incident-playbook.md` |

## Hard Rules — No Exceptions

- Never put API keys or passwords in code files or git repositories
- Never give an agent production database write access without an approval gate
- Never run agent-generated code on your main machine without sandbox testing first
- Never skip the security agent step before deploying code
- Never use the same API key for development and production
- Never expose services to the public internet without authentication and rate limiting
- Never let the system update its own dependencies without your explicit approval

## Quick Commands

```bash
# Check kill switch status
python tools/check-kill-switch.py

# View pending approvals
python tools/approval-queue.py list

# Approve an action
python tools/approval-queue.py approve <id>

# Reject an action
python tools/approval-queue.py reject <id> <reason>

# Emergency stop all agents
powershell -ExecutionPolicy Bypass -File tools\kill-switch.ps1

# Reset kill switch (after fixing the issue)
python tools/reset-kill-switch.py

# Run secret scan
gitleaks detect --source . --verbose
```
