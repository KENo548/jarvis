import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from vault_client import VaultClient, VaultSecret


class Phase3VaultClientTests(unittest.TestCase):
    def test_client_construction(self) -> None:
        client = VaultClient(addr="http://localhost:18201", token="test-token")
        self.assertEqual(client.addr, "http://localhost:18201")
        self.assertEqual(client.token, "test-token")

    def test_client_loads_token_from_file_or_empty(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="")
        # Token may be loaded from file or empty — either is valid
        self.assertIsInstance(client.token, str)

    def test_health_returns_sealed_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        h = client.health()
        self.assertTrue(h.get("sealed"))
        self.assertFalse(h.get("initialized"))

    def test_read_secret_returns_none_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        secret = client.read_secret("test/path")
        self.assertIsNone(secret)

    def test_read_secret_all_returns_none_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        result = client.read_secret_all("test/path")
        self.assertIsNone(result)

    def test_list_secrets_returns_empty_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        keys = client.list_secrets()
        self.assertEqual(keys, [])

    def test_write_secret_returns_false_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        result = client.write_secret("test/path", {"key": "value"})
        self.assertFalse(result)

    def test_renew_token_returns_false_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        result = client.renew_token()
        self.assertFalse(result)

    def test_token_info_returns_empty_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        info = client.token_info()
        self.assertEqual(info, {})

    def test_with_secrets_calls_func_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        called = [False]

        def my_func(val: str | None = None) -> str:
            called[0] = True
            return f"got:{val}"

        result = client.with_secrets("test/path", my_func)
        self.assertTrue(called[0])
        self.assertEqual(result, "got:None")

    def test_get_api_key_returns_none_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        key = client.get_api_key("anthropic")
        self.assertIsNone(key)

    def test_vault_secret_dataclass(self) -> None:
        s = VaultSecret(key="mykey", value="myvalue", version=2, created_at="2026-01-01T00:00:00")
        self.assertEqual(s.key, "mykey")
        self.assertEqual(s.value, "myvalue")
        self.assertEqual(s.version, 2)
        self.assertFalse(s.destroyed)

    def test_is_initialized_false_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        self.assertFalse(client.is_initialized())

    def test_is_unsealed_false_when_unreachable(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        self.assertFalse(client.is_unsealed())

    def test_auto_renew_does_nothing_when_not_needed(self) -> None:
        client = VaultClient(addr="http://localhost:1", token="x")
        client._renew_at = None
        client.auto_renew()  # Should not raise


if __name__ == "__main__":
    unittest.main()
