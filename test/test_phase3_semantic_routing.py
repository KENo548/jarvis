import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import capability_registry


class Phase3SemanticRoutingTests(unittest.TestCase):
    def test_route_task_returns_confidence_breakdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = capability_registry.route_task(
                "Please review this code for vulnerabilities and security issues",
                db_path=db_path,
            )

            self.assertEqual(result["selected_capability_id"], "security")
            self.assertIn("semantic_score", result)
            self.assertIn("historical_score", result)
            self.assertIn("validation_rate", result)
            self.assertGreaterEqual(result["confidence"], result["semantic_score"])

    def test_semantic_ranking_matches_human_baseline_for_research(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = capability_registry.route_task(
                "Search documentation and summarize findings for the new toolchain",
                db_path=db_path,
            )

            self.assertEqual(result["selected_capability_id"], "researcher")
            researcher = next(candidate for candidate in result["candidates"] if candidate["capability_id"] == "researcher")
            qa = next(candidate for candidate in result["candidates"] if candidate["capability_id"] == "qa")
            self.assertGreater(researcher["semantic_score"], qa["semantic_score"])


if __name__ == "__main__":
    unittest.main()