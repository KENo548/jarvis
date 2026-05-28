import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import sandbox_runner


class Phase3SandboxTests(unittest.TestCase):
    def test_run_python_snippet_isolated(self) -> None:
        result = sandbox_runner.run_python_snippet("print(2 + 2)")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "4")
        self.assertEqual(result.stderr.strip(), "")


if __name__ == "__main__":
    unittest.main()