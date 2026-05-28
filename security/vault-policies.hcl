# =============================================================================
# JARVIS Vault Policies — Applied via Vault CLI
# =============================================================================

# --- Agent Policy (applied to all agents) ---
# agents-policy.hcl
path "secret/data/agents/token-*" {
  capabilities = ["read"]
}

path "secret/data/agents/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/agents/*" {
  capabilities = ["read", "list"]
}

path "secret/data/system/*" {
  capabilities = ["deny"]
}

# --- API Key Policy (applied to service accounts) ---
# api-keys-policy.hcl
path "secret/data/api/*" {
  capabilities = ["read", "list"]
}

path "secret/data/api/anthropic" {
  capabilities = ["read"]
}

path "secret/data/api/github" {
  capabilities = ["read"]
}

# --- Admin Policy (applied to human users only) ---
# admin-policy.hcl
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/policy/*" {
  capabilities = ["read", "list", "create", "update", "delete"]
}

path "sys/auth/*" {
  capabilities = ["read", "list", "create", "update", "delete"]
}

path "sys/audit/*" {
  capabilities = ["read", "list", "create", "update", "delete"]
}

# --- Recovery Policy (emergency only — breaks glass) ---
# recovery-policy.hcl
path "sys/unseal" {
  capabilities = ["update", "sudo"]
}

path "sys/seal" {
  capabilities = ["update", "sudo"]
}

path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
