from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


SECURITY_DIR = Path(__file__).resolve().parent.parent / "security"
TOKEN_FILE = SECURITY_DIR / ".vault-root-token"
KEYS_FILE = SECURITY_DIR / ".vault-keys.json"

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://localhost:18201")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
VAULT_KV_PATH = os.environ.get("VAULT_KV_PATH", "secret/data/jarvis")


def _load_token_from_file() -> str:
    """Load root token from the setup file if env var is not set."""
    if VAULT_TOKEN:
        return VAULT_TOKEN
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    return ""


@dataclass(frozen=True)
class VaultSecret:
    key: str
    value: str
    version: int
    created_at: str
    destroyed: bool = False


class VaultClient:
    def __init__(
        self,
        addr: str = VAULT_ADDR,
        token: str = "",
        kv_mount: str = "secret",
    ):
        self.addr = addr.rstrip("/")
        self.token = token or _load_token_from_file()
        self.kv_mount = kv_mount
        self._renew_at: float | None = None

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = urljoin(f"{self.addr}/", path.lstrip("/"))
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, method=method)
        req.add_header("X-Vault-Token", self.token)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except URLError as e:
            raise ConnectionError(f"Vault connection failed: {e}") from e

    def health(self) -> dict[str, Any]:
        try:
            return self._request("GET", "/v1/sys/health")
        except ConnectionError:
            return {"sealed": True, "standby": True, "initialized": False}

    def is_initialized(self) -> bool:
        return self.health().get("initialized", False)

    def is_unsealed(self) -> bool:
        h = self.health()
        return bool(h.get("initialized")) and not h.get("sealed", True)

    def read_secret(self, path: str) -> VaultSecret | None:
        if not self.is_unsealed() or not self.token:
            return None
        try:
            resp = self._request("GET", f"/v1/{self.kv_mount}/data/{path.lstrip('/')}")
            data = resp.get("data", {})
            secret_data = data.get("data", {})
            metadata = data.get("metadata", {})
            keys = list(secret_data.keys())
            if not keys:
                return None
            key = keys[0]
            return VaultSecret(
                key=key,
                value=str(secret_data[key]),
                version=int(metadata.get("version", 1)),
                created_at=metadata.get("created_time", datetime.now(timezone.utc).isoformat()),
                destroyed=metadata.get("destroyed", False),
            )
        except (ConnectionError, json.JSONDecodeError, KeyError):
            return None

    def read_secret_all(self, path: str) -> dict[str, str] | None:
        """Read all key-value pairs from a secret path."""
        if not self.is_unsealed() or not self.token:
            return None
        try:
            resp = self._request("GET", f"/v1/{self.kv_mount}/data/{path.lstrip('/')}")
            data = resp.get("data", {})
            return data.get("data", {})
        except (ConnectionError, json.JSONDecodeError, KeyError):
            return None

    def list_secrets(self, path: str = "") -> list[str]:
        if not self.is_unsealed() or not self.token:
            return []
        try:
            resp = self._request("LIST", f"/v1/{self.kv_mount}/metadata/{path.lstrip('/')}")
            return resp.get("data", {}).get("keys", [])
        except (ConnectionError, json.JSONDecodeError, KeyError):
            return []

    def write_secret(self, path: str, data: dict[str, Any]) -> bool:
        if not self.is_unsealed() or not self.token:
            return False
        try:
            self._request("POST", f"/v1/{self.kv_mount}/data/{path.lstrip('/')}", {"data": data})
            return True
        except (ConnectionError, json.JSONDecodeError):
            return False

    def renew_token(self) -> bool:
        try:
            resp = self._request("POST", "/v1/auth/token/renew-self", {})
            ttl = resp.get("auth", {}).get("lease_duration", 0)
            if ttl > 0:
                self._renew_at = time.time() + (ttl * 0.5)
            return True
        except (ConnectionError, json.JSONDecodeError):
            return False

    def token_info(self) -> dict[str, Any]:
        try:
            return self._request("GET", "/v1/auth/token/lookup-self")
        except ConnectionError:
            return {}

    def auto_renew(self) -> None:
        if self._renew_at and time.time() >= self._renew_at:
            self.renew_token()

    def with_secrets(self, path: str, func: callable) -> Any:
        secret = self.read_secret(path)
        if secret is None:
            return func()
        return func(secret.value)

    def get_api_key(self, service: str) -> str | None:
        """Convenience: read an API key from secret/data/api/{service}."""
        secret = self.read_secret(f"api/{service}")
        if secret:
            return secret.value
        all_data = self.read_secret_all(f"api/{service}")
        if all_data:
            # Try common key names
            for key in ("api_key", "token", "key", "secret"):
                if key in all_data:
                    return str(all_data[key])
        return None


DEFAULT_VAULT = VaultClient()
