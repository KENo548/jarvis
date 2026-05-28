import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import durable_workflow


class Phase3DurableWorkflowTests(unittest.TestCase):
    def test_create_and_get_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workflows.db"
            run = durable_workflow.create_run("test_type", {"key": "value"}, db_path=db_path)
            self.assertEqual(run.workflow_type, "test_type")
            self.assertEqual(run.state, "pending")
            self.assertEqual(run.retry_count, 0)

            fetched = durable_workflow.get_run(run.run_id, db_path=db_path)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.run_id, run.run_id)
            self.assertEqual(fetched.state, "pending")

    def test_list_runs_returns_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workflows.db"
            run1 = durable_workflow.create_run("type_a", {"a": 1}, db_path=db_path)
            run2 = durable_workflow.create_run("type_b", {"b": 2}, db_path=db_path)
            runs = durable_workflow.list_runs(limit=10, db_path=db_path)
            self.assertEqual(len(runs), 2)
            self.assertEqual(runs[0].run_id, run2.run_id)

    def test_execute_workflow_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workflows.db"

            def step_a(inputs: dict) -> dict:
                return {"step_name": "step_a", "status": "ok", "value": inputs["x"] + 1}

            def step_b(inputs: dict) -> dict:
                prev = inputs["_step_a_result"]
                return {"step_name": "step_b", "status": "ok", "value": prev["value"] * 2}

            run = durable_workflow.execute_workflow(
                "test_pipeline",
                {"x": 5},
                steps=[("step_a", step_a), ("step_b", step_b)],
                db_path=db_path,
            )
            self.assertEqual(run.state, "completed")
            self.assertEqual(run.retry_count, 0)
            result = json.loads(run.result_json)
            self.assertEqual(result["_step_a_result"]["value"], 6)
            self.assertEqual(result["_step_b_result"]["value"], 12)

    def test_execute_workflow_retry_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workflows.db"
            attempt_count = [0]

            def flaky_step(inputs: dict) -> dict:
                attempt_count[0] += 1
                if attempt_count[0] < 3:
                    raise ValueError("transient failure")
                return {"step_name": "flaky", "status": "ok", "value": 42}

            run = durable_workflow.execute_workflow(
                "test_flaky",
                {"x": 1},
                steps=[("flaky", flaky_step)],
                max_retries=3,
                db_path=db_path,
            )
            self.assertEqual(run.state, "completed")
            self.assertEqual(attempt_count[0], 3)

    def test_execute_workflow_gives_up_after_max_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workflows.db"

            def always_fails(inputs: dict) -> dict:
                raise RuntimeError("always fails")

            run = durable_workflow.execute_workflow(
                "test_fail",
                {"x": 1},
                steps=[("failing", always_fails)],
                max_retries=2,
                db_path=db_path,
            )
            self.assertEqual(run.state, "failed")
            self.assertIsNotNone(run.error)

    def test_retry_failed_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workflows.db"
            attempt_count = [0]

            def flaky_step(inputs: dict) -> dict:
                attempt_count[0] += 1
                if attempt_count[0] < 2:
                    raise ValueError("transient")
                return {"step_name": "flaky", "status": "ok", "value": 99}

            run = durable_workflow.execute_workflow(
                "test_retry_fail",
                {"x": 1},
                steps=[("flaky", flaky_step)],
                max_retries=0,
                db_path=db_path,
            )
            self.assertEqual(run.state, "failed")

            durable_workflow.retry_failed_run(run.run_id, db_path=db_path)
            attempt_count[0] = 0

            run2 = durable_workflow.execute_workflow(
                "test_retry_fail",
                {"x": 1},
                steps=[("flaky", flaky_step)],
                max_retries=3,
                db_path=db_path,
            )
            self.assertEqual(run2.state, "completed")

    def test_backoff_delay_increases(self) -> None:
        delays = [durable_workflow._backoff_delay(i) for i in range(1, 5)]
        for i in range(1, len(delays)):
            self.assertGreater(delays[i], delays[i - 1])


if __name__ == "__main__":
    unittest.main()
