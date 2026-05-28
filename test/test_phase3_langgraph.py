import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import capability_registry
import langgraph_pipeline
import orchestration_graph


class Phase3LangGraphTests(unittest.TestCase):
    def test_pipeline_returns_seven_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = langgraph_pipeline.run_pipeline(
                "Research the latest AI frameworks",
                db_path=db_path,
            )
            node_names = [n["name"] for n in result["nodes"]]
            self.assertEqual(len(node_names), 7)
            self.assertEqual(result["graph"], "langgraph-v1")

    def test_pipeline_skips_research_when_not_needed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = langgraph_pipeline.run_pipeline(
                "Fix the login button color",
                db_path=db_path,
            )
            research = next(n for n in result["nodes"] if n["name"] == "research")
            self.assertEqual(research["status"], "skipped")

    def test_pipeline_runs_sandbox_for_code_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = langgraph_pipeline.run_pipeline(
                "Write a test function for the API",
                db_path=db_path,
            )
            sandbox = next(n for n in result["nodes"] if n["name"] == "sandbox")
            self.assertEqual(sandbox["status"], "ok")
            qa = next(n for n in result["nodes"] if n["name"] == "qa")
            self.assertEqual(qa["status"], "ok")

    def test_pipeline_routes_through_security_for_write_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = langgraph_pipeline.run_pipeline(
                "Write a new API endpoint",
                db_path=db_path,
            )
            security = next(n for n in result["nodes"] if n["name"] == "security")
            self.assertIn(security["status"], ("ok", "warn"))
            self.assertIsNotNone(security["output"].get("warnings"))

    def test_pipeline_execute_skipped_without_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = langgraph_pipeline.run_pipeline(
                "Refactor the authentication module",
                db_path=db_path,
            )
            execute = next(n for n in result["nodes"] if n["name"] == "execute")
            self.assertEqual(execute["status"], "skipped")
            self.assertIn("no approvals", execute["output"].get("reason", ""))

    def test_orchestration_graph_returns_execution_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = orchestration_graph.run_graph(
                "Research quantum computing trends",
                db_path=db_path,
            )
            self.assertIn("execution_backend", result)
            self.assertIn(result["execution_backend"], ("temporal", "local-durable"))
            self.assertIn("nodes", result)
            self.assertGreater(len(result["nodes"]), 0)

    def test_orchestration_graph_list_runs(self) -> None:
        runs = orchestration_graph.list_graph_runs(limit=5)
        self.assertIsInstance(runs, list)


if __name__ == "__main__":
    unittest.main()
