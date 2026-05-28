import json
import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import audit_log


class Phase3AuditLogTests(unittest.TestCase):
    def test_append_entry_creates_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "audit.log"
            audit_log.append_entry("test_event", "hello world", log_path=log_path, foo="bar")
            audit_log.append_entry("test_event", "second event", log_path=log_path, baz=1)

            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            self.assertEqual(first["event_type"], "test_event")
            self.assertEqual(first["detail"], "hello world")
            self.assertEqual(first["metadata"]["foo"], "bar")


if __name__ == "__main__":
    unittest.main()