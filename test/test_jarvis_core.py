import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import capability_registry
import commander
import governance
import jarvis_metrics
import runtime_lifecycle
import workflow_dispatcher


class JarvisCoreTests(unittest.TestCase):
    def test_runtime_lifecycle_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            create_approval = governance.enqueue_approval(
                agent_id="agent.coder",
                action_type="create_runtime",
                action_detail="Create runtime task-123",
                risk_level="high",
                db_path=db_path,
            )
            governance.approve_action(create_approval, db_path=db_path)
            runtime = runtime_lifecycle.create_runtime(
                task_id="task-123",
                capability_id="coder",
                agent_id="agent.coder",
                requested_action="write tests",
                approval_id=create_approval,
                db_path=db_path,
            )
            self.assertEqual(runtime.state, "CREATED")

            run_approval = governance.enqueue_approval(
                agent_id="runtime",
                action_type="runtime_transition",
                action_detail=f"{runtime.runtime_id}: CREATED -> RUNNING",
                risk_level="medium",
                db_path=db_path,
            )
            governance.approve_action(run_approval, db_path=db_path)
            started = runtime_lifecycle.start_runtime_with_approval(runtime.runtime_id, run_approval, db_path=db_path)
            self.assertEqual(started.state, "RUNNING")

            complete_approval = governance.enqueue_approval(
                agent_id="runtime",
                action_type="runtime_transition",
                action_detail=f"{runtime.runtime_id}: RUNNING -> COMPLETED",
                risk_level="high",
                db_path=db_path,
            )
            governance.approve_action(complete_approval, db_path=db_path)
            completed = runtime_lifecycle.complete_runtime_with_approval(runtime.runtime_id, None, complete_approval, db_path=db_path)
            self.assertEqual(completed.state, "TERMINATED")

            stored = runtime_lifecycle.get_runtime(runtime.runtime_id, db_path=db_path)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.state, "TERMINATED")

    def test_registry_routes_security_tasks_to_security(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = capability_registry.route_task(
                "Please audit this code for security vulnerabilities and secrets",
                db_path=db_path,
            )

            self.assertEqual(result["selected_capability_id"], "security")
            self.assertGreater(result["confidence"], 0.35)

    def test_metrics_export_includes_registry_and_runtime_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)
            approval_id = governance.enqueue_approval(
                agent_id="agent.security",
                action_type="create_runtime",
                action_detail="Create runtime task-456",
                risk_level="high",
                db_path=db_path,
            )
            governance.approve_action(approval_id, db_path=db_path)
            runtime_lifecycle.create_runtime(
                task_id="task-456",
                capability_id="security",
                agent_id="agent.security",
                requested_action="audit",
                approval_id=approval_id,
                db_path=db_path,
            )

            metrics = jarvis_metrics.build_metrics(db_path=db_path)

            self.assertIn('jarvis_capabilities_enabled_total 7', metrics)
            self.assertIn('jarvis_runtime_instances_total{state="CREATED"} 1', metrics)
            self.assertIn('jarvis_pending_approvals_total 0', metrics)

    def test_commander_routes_and_opens_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = commander.plan_task(
                "Please audit the code for secrets and vulnerabilities",
                agent_id="agent.orchestrator",
                db_path=db_path,
            )

            self.assertEqual(result["selected_capability_id"], "security")
            approval = governance.get_approval(result["approval_id"], db_path=db_path)
            self.assertIsNotNone(approval)
            self.assertEqual(approval["status"], "pending")

    def test_workflow_dispatcher_executes_approved_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            preview = workflow_dispatcher.dispatch_task(
                "Please write tests for the runtime lifecycle",
                agent_id="agent.orchestrator",
                db_path=db_path,
            )
            self.assertEqual(preview["workflow_state"], "AWAITING_APPROVAL")

            create_approval = governance.enqueue_approval(
                agent_id="agent.orchestrator",
                action_type="create_runtime",
                action_detail="Create approved runtime for workflow",
                risk_level="high",
                db_path=db_path,
            )
            start_approval = governance.enqueue_approval(
                agent_id="runtime",
                action_type="runtime_transition",
                action_detail="Approved workflow start",
                risk_level="medium",
                db_path=db_path,
            )
            complete_approval = governance.enqueue_approval(
                agent_id="runtime",
                action_type="runtime_transition",
                action_detail="Approved workflow completion",
                risk_level="high",
                db_path=db_path,
            )
            governance.approve_action(create_approval, db_path=db_path)
            governance.approve_action(start_approval, db_path=db_path)
            governance.approve_action(complete_approval, db_path=db_path)

            result = workflow_dispatcher.execute_approved_task(
                "Please write tests for the runtime lifecycle",
                approval_id=create_approval,
                start_approval_id=start_approval,
                complete_approval_id=complete_approval,
                agent_id="agent.orchestrator",
                db_path=db_path,
            )

            self.assertEqual(result["state"], "TERMINATED")
            self.assertEqual(result["started_state"], "RUNNING")


if __name__ == "__main__":
    unittest.main()