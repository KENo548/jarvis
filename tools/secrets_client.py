"""
JARVIS Secrets Client — Free-tier secrets management using OS keyring.

Uses the operating system's native credential store:
  - Windows: Windows Credential Locker
  - macOS: Keychain
  - Linux: Secret Service (GNOME Keyring / KWallet)

No subscription required. No third-party service needed.

Usage:
  python tools/secrets_client.py set <service> <key> <value>
  python tools/secrets_client.py get <service> <key>
  python tools/secrets_client.py delete <service> <key>
  python tools/secrets_client.py list <service>
  python tools/secrets_client.py migrate-vault <vault_addr> <vault_token>
"""

import sys
import json

try:
    import keyring
except ImportError:
    print("Installing keyring...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "keyring", "-q"])
    import keyring

SERVICE_PREFIX = "jarvis"


def set_secret(service: str, key: str, value: str) -> None:
    """Store a secret in the OS keyring."""
    full_service = f"{SERVICE_PREFIX}/{service}"
    keyring.set_password(full_service, key, value)
    # Update registry
    reg = _load_registry()
    svc_keys = reg.get(full_service, [])
    if key not in svc_keys:
        svc_keys.append(key)
    reg[full_service] = svc_keys
    _save_registry(reg)
    print(f"OK: Stored {full_service}/{key}")


def get_secret(service: str, key: str) -> str | None:
    """Retrieve a secret from the OS keyring."""
    full_service = f"{SERVICE_PREFIX}/{service}"
    value = keyring.get_password(full_service, key)
    if value:
        print(value)
    else:
        print(f"NOT FOUND: {full_service}/{key}", file=sys.stderr)
        sys.exit(1)
    return value


def delete_secret(service: str, key: str) -> None:
    """Delete a secret from the OS keyring."""
    full_service = f"{SERVICE_PREFIX}/{service}"
    try:
        keyring.delete_password(full_service, key)
        # Update registry
        reg = _load_registry()
        svc_keys = reg.get(full_service, [])
        if key in svc_keys:
            svc_keys.remove(key)
            reg[full_service] = svc_keys
            _save_registry(reg)
        print(f"OK: Deleted {full_service}/{key}")
    except keyring.errors.PasswordDeleteError:
        print(f"NOT FOUND: {full_service}/{key}", file=sys.stderr)
        sys.exit(1)


def _registry_path() -> str:
    """Path to the local secret registry (tracks which keys exist)."""
    import pathlib
    return str(pathlib.Path(__file__).resolve().parent.parent / "security" / ".secret-registry.json")


def _load_registry() -> dict:
    import pathlib, json
    p = pathlib.Path(_registry_path())
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_registry(reg: dict) -> None:
    import pathlib, json
    p = pathlib.Path(_registry_path())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, indent=2))


def list_secrets(service: str) -> None:
    """List all stored secret keys for a service (values not shown)."""
    reg = _load_registry()
    svc_key = f"{SERVICE_PREFIX}/{service}"
    keys = reg.get(svc_key, [])
    if keys:
        print(f"Secrets stored under {svc_key}:")
        for k in keys:
            print(f"  - {k}")
    else:
        print(f"No secrets found under {svc_key}")


def migrate_from_vault(vault_addr: str, vault_token: str) -> None:
    """
    One-time migration: pull secrets from HashiCorp Vault and store in OS keyring.
    This allows agents to use the local keyring instead of requiring Vault to be running.
    """
    import urllib.request

    paths = [
        "secret/data/api/anthropic",
        "secret/data/api/github",
        "secret/data/agents/coder",
        "secret/data/agents/researcher",
        "secret/data/system/monitoring",
    ]

    migrated = 0
    for path in paths:
        try:
            req = urllib.request.Request(
                f"{vault_addr}/v1/{path}",
                headers={"X-Vault-Token": vault_token},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                secrets = data.get("data", {}).get("data", {})
                for k, v in secrets.items():
                    if v and v != "TO_BE_SET":
                        service_name = path.replace("secret/data/", "").replace("/", "_")
                        set_secret(service_name, k, v)
                        migrated += 1
        except Exception as e:
            print(f"  SKIP {path}: {e}", file=sys.stderr)

    print(f"\nMigrated {migrated} secrets from Vault to OS keyring.")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    service = sys.argv[2] if len(sys.argv) > 2 else ""

    if command == "set":
        if len(sys.argv) < 5:
            print("Usage: secrets_client.py set <service> <key> <value>")
            sys.exit(1)
        set_secret(service, sys.argv[3], sys.argv[4])
    elif command == "get":
        if len(sys.argv) < 4:
            print("Usage: secrets_client.py get <service> <key>")
            sys.exit(1)
        get_secret(service, sys.argv[3])
    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: secrets_client.py delete <service> <key>")
            sys.exit(1)
        delete_secret(service, sys.argv[3])
    elif command == "list":
        list_secrets(service)
    elif command == "migrate-vault":
        if len(sys.argv) < 4:
            print("Usage: secrets_client.py migrate-vault <vault_addr> <vault_token>")
            sys.exit(1)
        migrate_from_vault(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
