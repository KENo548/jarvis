# JARVIS Incident Response Playbook

## When to Use This Playbook

Activate this playbook when any of the following occur:

- An agent behaves unexpectedly or produces harmful output
- A secret or API key is suspected to be leaked
- A service is compromised or unavailable
- An intrusion or unauthorized access is detected
- The kill switch has been triggered

---

## Play 1: Agent Misbehavior

**Symptoms**: Agent takes actions you didn't approve, produces gibberish, loops infinitely, or ignores instructions.

1. **Trigger the kill switch immediately**
   - Windows: `powershell -ExecutionPolicy Bypass -File tools\kill-switch.ps1`
   - Linux/Mac: `./tools/kill-switch.sh`

2. **Check the audit log**
   - Review `logs/audit.log` for the agent's recent actions
   - Look for unusual patterns: repeated failures, unauthorized file access, unexpected API calls

3. **Revoke the agent's credentials**
   - If using Vault: `vault token revoke <agent-token>`
   - If using API keys: rotate the key immediately

4. **Review the agent's prompt and tools**
   - Check `agents/<agent-name>/config.json` for misconfigured permissions
   - Check if prompt injection is possible — review what external content was passed to the agent

5. **Analyze root cause**
   - Was it a prompt injection attack?
   - Was it a model failure (wrong output)?
   - Was it a tool misconfiguration?

6. **Document the incident**
   - Open an issue in your documentation system
   - Update this playbook with any new response steps

7. **Restart the agent**
   - Reset the kill switch: `python tools/reset-kill-switch.py`
   - Restart the agent with corrected configuration
   - Monitor the first 10 minutes of operation closely

---

## Play 2: Secret / API Key Leak

**Symptoms**: Alert from git-secrets, GitHub notification of exposed key, unexpected API usage in billing.

1. **Immediately rotate the compromised credential**
   - Anthropic API key: Rotate in Anthropic Console
   - GitHub token: Regenerate in GitHub Settings
   - Any other API key: Rotate at the provider

2. **Check git history for exposed secrets**
   ```bash
   git log --all --oneline | xargs -I{} sh -c 'git show {} | grep -i "sk-\\|ghp_\\|api_key"'
   ```
   - If found, use `git filter-repo` or `bfg` to purge secrets from history
   - Force-push the cleaned history

3. **Revoke and recreate all affected tokens**
   - Assume any token in the same codebase or config is compromised
   - Rotate proactively

4. **Check cloud provider for unauthorized activity**
   - Review API usage logs
   - Check for unusual access patterns

5. **Update git-secrets patterns**
   - Ensure the leaked format is covered by the secret scanner
   - Run `./tools/git-secrets-setup.sh`

6. **Document and learn**
   - How did the secret get into the codebase?
   - What process change prevents this from recurring?

---

## Play 3: Service Compromise / Intrusion

**Symptoms**: Falco alert, unexpected network connections, unauthorized file changes, unknown processes.

1. **Isolate the affected system**
   - Disconnect from the network
   - Stop Docker containers: `docker-compose down`
   - Trigger the kill switch

2. **Preserve evidence**
   - Copy logs: `logs/`, Docker container logs
   - Take a snapshot of the system state
   - Do NOT reboot before evidence is collected

3. **Identify the entry point**
   - Review auth logs (SSH, API, web)
   - Check for exposed services (scan open ports)
   - Look for weak or default credentials

4. **Contain the breach**
   - Rotate ALL secrets and API keys
   - Change ALL passwords
   - Revoke ALL active tokens
   - Block the attacker's IP range

5. **Eradicate**
   - Wipe and restore affected systems from backup
   - Update firewall rules
   - Patch the vulnerability

6. **Recover**
   - Restore from clean backup
   - Verify system integrity
   - Gradually reintroduce services

7. **Post-mortem**
   - Document the incident timeline
   - Identify process failures
   - Update security controls
   - Practice quarterly

---

## Play 4: Kill Switch Activated (Recovery)

**Symptoms**: Agents stopped. Pending actions rejected. System in lockdown.

1. **Verify the cause**
   - Check `logs/audit.log` for the kill switch entry
   - Review `logs/` for agent errors
   - Talk to any team members who may have triggered it

2. **Fix the underlying issue**
   - Apply the fix from the relevant play above
   - Ensure the root cause is addressed

3. **Reset the kill switch**
   ```bash
   python tools/reset-kill-switch.py
   ```

4. **Restart services**
   ```bash
   cd infrastructure
   docker-compose up -d
   ```

5. **Verify system health**
   - Check agent status
   - Verify database connectivity
   - Run a test task

6. **Monitor for recurrence**
   - Watch the first hour closely
   - Set up additional alerting if needed

---

## Emergency Contact Information

- **Anthropic Support**: support@anthropic.com (API key issues)
- **GitHub Support**: github.com/contact (token issues)
- **Vault Emergency**: Local unseal keys stored in Bitwarden

---

## Quarterly Practice Schedule

- Month 1: Play 1 (Agent Misbehavior)
- Month 2: Play 2 (Secret Leak)
- Month 3: Play 3 (Intrusion)
- Month 4: Full system restore from backup

Document each practice session and update this playbook based on lessons learned.
