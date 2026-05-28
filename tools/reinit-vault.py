#!/usr/bin/env python3
"""Re-initialize Vault and save credentials to security/."""
import json
import sys
import time
import urllib.request
from pathlib import Path

VAULT_ADDR = "http://localhost:18201"
SECURITY_DIR = Path(__file__).resolve().parent.parent / "security"

def vault_request(path, method="GET", data=None):
    url = f"{VAULT_ADDR}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": True, "code": e.code, "body": body}

# Wait for Vault to be ready
print("Waiting for Vault to be ready...")
for i in range(20):
    try:
        health = vault_request("/v1/sys/health")
        if "error" not in health or health.get("code") != 501:
            break
    except Exception:
        pass
    time.sleep(2)
    print(f"  Attempt {i+1}/20...")

health = vault_request("/v1/sys/health")
print(f"Vault state: {json.dumps({k: health.get(k) for k in ['initialized', 'sealed', 'version']}, indent=2)}")

if health.get("initialized"):
    print("Vault already initialized. Checking if we have a token...")
    token_file = SECURITY_DIR / ".vault-root-token"
    if token_file.exists():
        print(f"Token file exists: {token_file}")
    else:
        print("No token file. Vault was initialized externally.")
        print("Options:")
        print("  1. Find the token from docker logs: docker logs jarvis-vault")
        print("  2. Re-initialize: docker volume rm infrastructure_vault-data && docker compose up -d vault")
    sys.exit(0)

# Initialize
print("\nInitializing Vault with 5 key shares (threshold 3)...")
result = vault_request("/v1/sys/init", "POST", {"secret_shares": 5, "secret_threshold": 3})
if "error" in result:
    print(f"Init failed: {result}")
    sys.exit(1)

# Save keys
keys_file = SECURITY_DIR / ".vault-keys.json"
keys_file.parent.mkdir(parents=True, exist_ok=True)
keys_file.write_text(json.dumps({
    "keys": result["keys"],
    "keys_base64": result["keys_base64"],
    "threshold": 3,
}, indent=2))
print(f"Saved unseal keys to {keys_file}")

# Save root token
token_file = SECURITY_DIR / ".vault-root-token"
token_file.write_text(result["root_token"])
print(f"Saved root token to {token_file}")

# Unseal with first 3 keys
print("\nUnsealing Vault...")
for i in range(3):
    unseal_result = vault_request("/v1/sys/unseal", "POST", {"key": result["keys"][i]})
    sealed = unseal_result.get("sealed", True)
    print(f"  Key {i+1}/3 applied. Sealed: {sealed}")

# Store initial secrets
token = result["root_token"]
print("\nStoring initial secrets...")

def store_secret(path, data):
    resp = vault_request(f"/v1/secret/data/{path}", "POST", {"data": data})
    if "error" in resp:
        print(f"  Failed to store {path}: {resp}")
    else:
        print(f"  Stored: {path}")

store_secret("api/anthropic", {"api_key": "TO_BE_SET", "model": "claude-sonnet-4-20250514"})
store_secret("api/github", {"token": "TO_BE_SET"})
store_secret("agents/coder", {"name": "coder-001", "permissions": "filesystem,github,sandbox"})
store_secret("agents/researcher", {"name": "researcher-001", "permissions": "browser,search,fetch"})

print("\n=== Vault Setup Complete ===")
print(f"Root token: {token[:12]}...")
print(f"Keys saved: {keys_file}")
print(f"Token saved: {token_file}")
print(f"Set in environment: VAULT_ADDR={VAULT_ADDR}")
print(f"Set in environment: VAULT_TOKEN={token}")
