import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import capability_registry
import governance
import orchestration_graph


class Phase3OrchestrationUpgradeTests(unittest.TestCase):
    def test_get_graph_run_returns_none_for_missing(self) -> None:
        result = orchestration_graph.get_graph_run("nonexistent-run-id")
        self.assertIsNone(result)

    def test_graph_run_persists_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = orchestration_graph.run_graph(
                "Fix a bug in the authentication code",
                db_path=db_path,
                max_retries=1,
            )

            run_id = result["run_id"]
            self.assertIsNotNone(run_id)

            fetched = orchestration_graph.get_graph_run(run_id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["run_id"], run_id)
            self.assertEqual(fetched["state"], "completed")

    def test_run_id_is_unique_per_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            r1 = orchestration_graph.run_graph("research memory usage patterns", db_path=db_path)
            r2 = orchestration_graph.run_graph("research memory usage patterns", db_path=db_path)
            self.assertNotEqual(r1["run_id"], r2["run_id"])

    def test_list_graph_runs_returns_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            orchestration_graph.run_graph("Write a test function", db_path=db_path)
            orchestration_graph.run_graph("Research documentation", db_path=db_path)

            runs = orchestration_graph.list_graph_runs(limit=10)
            self.assertGreaterEqual(len(runs), 2)

    def test_graph_includes_run_id_and_retry_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = orchestration_graph.run_graph("Plan the project roadmap", db_path=db_path)
            self.assertIn("run_id", result)
            self.assertIn("retry_count", result)
            self.assertIn("graph", result)
            self.assertEqual(result["graph"], "langgraph-v1")

    def test_graph_all_seven_nodes_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = orchestration_graph.run_graph("Write tests for the API", db_path=db_path)
            node_names = [n["name"] for n in result["nodes"]]
            self.assertEqual(node_names, ["plan", "route", "research", "sandbox", "qa", "security", "execute"])


if __name__ == "__main__":
    unittest.main()
