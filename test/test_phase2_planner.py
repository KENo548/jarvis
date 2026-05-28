import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import memory_store
import planner_tool


class Phase2PlannerTests(unittest.TestCase):
    def test_planner_uses_memory_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            vault_path = Path(temp_dir) / "vault"
            memory_store.store_note(
                title="Research digest",
                content="Researcher should search, store findings, and summarize results.",
                source_type="research",
                source_ref="docs/ROADMAP.md#phase2",
                tags=["research", "memory"],
                db_path=db_path,
            )

            plan = planner_tool.build_plan(
                "Create a research plan for memory and search improvements",
                db_path=db_path,
                vault_path=vault_path,
            )

            self.assertEqual(plan["risk_level"], "medium")
            self.assertGreaterEqual(plan["estimated_steps"], 3)
            self.assertTrue(plan["context_notes"])
            self.assertTrue(any(p.suffix == ".md" for p in vault_path.iterdir()))


if __name__ == "__main__":
    unittest.main()