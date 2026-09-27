from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract, resolve_role
from app.db import create_project, initialize_database
from app.organization import DevOpsAgent


class DevOpsAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project(
            "DevOps project",
            "Controlled deployment workflow",
            database_path=self.path,
        )
        self.devops = DevOpsAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Deploy release") -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Plan and verify an application deployment",
            role="devops",
            expected_outputs=("DeploymentPlan", "DeploymentResult"),
            acceptance_criteria=("Health and smoke checks pass before release completion",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def _production_plan(self):
        task = self._task()
        plan = self.devops.create_plan(
            task.id,
            release_candidate="release-2026.09.19",
            environment="production",
            operations=("production_deployment", "service_restart"),
            configuration_files=("deploy/windows-server/web.config",),
            changed_files=("services/orchestrator/app/main.py",),
            health_endpoint="http://127.0.0.1:8012/health",
            smoke_tests=("health endpoint", "coordination roles endpoint"),
            rollback_steps=("restore checkpoint", "restart known-good service"),
        )
        return task, plan

    def test_deployment_contract_and_profile_are_scoped(self) -> None:
        contract = get_role_contract("devops")
        self.assertEqual(contract.write_permission, WritePermission.SCOPED)
        self.assertIn("deploy", contract.allowed_tools)
        self.assertIn("health_check", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("assigned_scope", "assigned_deployment_config", "assigned_operational_scripts"))
        self.assertIn("rollback_strategy", contract.capabilities)
        self.assertIn("approval_gate_rate", contract.performance_signals)
        self.assertEqual(resolve_role("deployment-engineer"), "devops")
        profile = self.devops.ensure_profile()
        self.assertEqual(profile.role, "devops")
        self.assertEqual(profile.department.value, "OPERATIONS")

    def test_high_risk_deployment_plan_requires_approval(self) -> None:
        task, plan = self._production_plan()
        self.assertTrue(plan.requires_approval)
        self.assertEqual(plan.status, "awaiting_approval")
        with self.assertRaises(PermissionError):
            self.devops.deploy(plan, executor=lambda _: True, health_checker=lambda: True, smoke_runner=lambda: True)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn("deployment_approval_gate", {row["topic"] for row in messages})

    def test_approval_health_and_smoke_checks_complete_deployment(self) -> None:
        task, plan = self._production_plan()
        approval = self.devops.approve_plan(
            plan,
            approved_by="owner-policy",
            approval_reference="CHANGE-2026-0919",
            scope=("production", "service-restart"),
        )
        result = self.devops.deploy(
            plan,
            approval=approval,
            executor=lambda _: True,
            health_checker=lambda: {"ok": True},
            smoke_runner=lambda: {"passed": True},
        )

        self.assertTrue(result.success)
        self.assertTrue(result.health_passed)
        self.assertTrue(result.smoke_passed)
        self.assertFalse(result.rolled_back)
        self.assertEqual(result.status, "succeeded")
        self.assertTrue(result.handoff_id)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        message_types = {row["message_type"] for row in messages}
        self.assertIn(MessageType.DECISION.value, message_types)
        self.assertIn(MessageType.RESULT.value, message_types)

    def test_failed_deployment_runs_rollback(self) -> None:
        _, plan = self._production_plan()
        approval = self.devops.approve_plan(
            plan,
            approved_by="owner-policy",
            approval_reference="CHANGE-FAILED-1",
        )
        rollback_calls: list[tuple[str, ...]] = []

        def rollback(steps: tuple[str, ...]) -> bool:
            rollback_calls.append(steps)
            return True

        result = self.devops.deploy(
            plan,
            approval=approval,
            executor=lambda _: (_ for _ in ()).throw(RuntimeError("service failed to start")),
            rollback_executor=rollback,
        )

        self.assertFalse(result.success)
        self.assertTrue(result.rolled_back)
        self.assertEqual(result.status, "rolled_back")
        self.assertEqual(len(rollback_calls), 1)
        self.assertIn("service failed to start", result.error or "")

    def test_health_failure_rolls_back_after_deployment(self) -> None:
        _, plan = self._production_plan()
        approval = self.devops.approve_plan(
            plan,
            approved_by="owner-policy",
            approval_reference="CHANGE-HEALTH-1",
        )
        result = self.devops.deploy(
            plan,
            approval=approval,
            executor=lambda _: True,
            health_checker=lambda: False,
            smoke_runner=lambda: False,
            rollback_executor=lambda _: True,
        )

        self.assertFalse(result.success)
        self.assertFalse(result.health_passed)
        self.assertFalse(result.smoke_passed)
        self.assertTrue(result.rolled_back)
        self.assertEqual(result.status, "rolled_back")


if __name__ == "__main__":
    unittest.main()


