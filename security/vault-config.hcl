# =============================================================================
# JARVIS HashiCorp Vault Configuration
# Path: jarvis/security/vault-config.hcl
# =============================================================================

storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8201"
  tls_disable = true
  # Production: enable TLS and use a proper certificate
  # tls_cert_file = "/vault/config/cert.pem"
  # tls_key_file  = "/vault/config/key.pem"
}

api_addr = "http://0.0.0.0:8201"

ui = true

# =============================================================================
# Security Policies
# =============================================================================

# Agent policy — minimum permissions for agent secret access
path "secret/data/agents/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/agents/*" {
  capabilities = ["read", "list"]
}

# Admin policy — full access
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/*" {
  capabilities = ["read", "sudo"]
}

# Audit log policy — append-only
path "sys/audit/*" {
  capabilities = ["create", "read", "sudo"]
}
