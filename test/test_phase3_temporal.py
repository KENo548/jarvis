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
import temporal_integration
import orchestration_graph


class Phase3TemporalTests(unittest.TestCase):
    def test_temporal_module_imports(self) -> None:
        self.assertTrue(hasattr(temporal_integration, "run_pipeline_durable"))
        self.assertTrue(hasattr(temporal_integration, "run_pipeline_via_temporal"))
        self.assertTrue(hasattr(temporal_integration, "start_worker"))

    def test_temporal_availability_flag(self) -> None:
        self.assertIn(temporal_integration.TEMPORAL_AVAILABLE, (True, False))

    def test_is_temporal_reachable(self) -> None:
        result = temporal_integration._is_temporal_reachable()
        self.assertIsInstance(result, bool)

    def test_run_pipeline_durable_falls_back_to_local(self) -> None:
        """When Temporal is unreachable, should fall back to local durable workflow."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = temporal_integration.run_pipeline_durable(
                "Fix the login button color",
                db_path=db_path,
            )
            self.assertIn("execution_backend", result)
            self.assertIn(result["execution_backend"], ("temporal", "local-durable"))
            self.assertIn("nodes", result)
            self.assertGreater(len(result["nodes"]), 0)

    def test_run_pipeline_durable_returns_correct_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = temporal_integration.run_pipeline_durable(
                "Research AI frameworks",
                db_path=db_path,
            )
            self.assertIn("task_text", result)
            self.assertIn("graph", result)
            self.assertIn("nodes", result)
            self.assertIn("final_state", result)
            self.assertIn("execution_backend", result)

    def test_orchestration_graph_delegates_to_temporal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = orchestration_graph.run_graph(
                "Research quantum computing trends",
                db_path=db_path,
            )
            self.assertIn("execution_backend", result)
            self.assertIn("nodes", result)

    def test_pipeline_input_dataclass(self) -> None:
        inp = temporal_integration.PipelineInput(
            task_text="test",
            agent_id="test-agent",
            db_path="/tmp/test.db",
            approvals_json="{}",
            vault_path=None,
        )
        self.assertEqual(inp.task_text, "test")
        self.assertEqual(inp.agent_id, "test-agent")

    def test_pipeline_output_dataclass(self) -> None:
        out = temporal_integration.PipelineOutput(result_json="{}")
        self.assertEqual(out.result_json, "{}")


if __name__ == "__main__":
    unittest.main()
