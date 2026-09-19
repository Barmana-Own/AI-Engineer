from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.collaboration_store import list_decisions
from app.coordination.models import CoordinationTask, MessageType, TaskState, WritePermission
from app.coordination.project_management import list_work_queue, set_quality_gate
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import EngineeringManagerAgent


class EngineeringManagerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Engineering project", "Technical execution", database_path=self.path)
        self.manager = EngineeringManagerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, *, role: str, title: str | None = None, expected_outputs: tuple[str, ...] = ()) -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title or f"{role} task",
            description="technical task",
            role=role,
            expected_outputs=expected_outputs,
            writer=role in {"backend", "frontend", "implementer"},
        )
        store.create_task(task, database_path=self.path)
        return task

    def _running(self, task: CoordinationTask) -> None:
        store.transition(task.id, TaskState.READY, database_path=self.path)
        store.transition(task.id, TaskState.ASSIGNED, assigned_agent=task.role, database_path=self.path)
        store.transition(task.id, TaskState.RUNNING, database_path=self.path)

    def test_role_contract_and_profile_are_least_privilege(self) -> None:
        contract = get_role_contract("engineering_manager")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("technical_task_delegation", contract.capabilities)
        self.assertIn("technical_readiness", contract.capabilities)
        profile = self.manager.ensure_profile()
        self.assertEqual(profile.role, "engineering_manager")
        self.assertEqual(profile.write_permission, WritePermission.READ_ONLY.value)

    def test_technical_task_delegation_persists_assignment_queue_and_handoff(self) -> None:
        task = self._task(role="backend")
        result = self.manager.delegate_task(task.id, "backend", rationale="Backend owns the API contract.", evidence=("requirements:FR-001",))
        self.assertEqual(result.status, "assigned")
        self.assertEqual(store.get_task(task.id, database_path=self.path)["assigned_agent"], "backend")
        queue = list_work_queue(agent_id="backend", project_id=self.project["id"], database_path=self.path)
        self.assertEqual(len(queue), 1)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual(messages[0]["message_type"], MessageType.HANDOFF.value)

    def test_agent_reassignment_preserves_audit_message(self) -> None:
        task = self._task(role="backend")
        self.manager.delegate_task(task.id, "backend", rationale="Initial assignment")
        result = self.manager.reassign_task(task.id, "frontend", reason="API ownership moved")
        self.assertEqual(result.assigned_role, "frontend")
        self.assertEqual(store.get_task(task.id, database_path=self.path)["assigned_agent"], "frontend")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertGreaterEqual(len(messages), 2)

    def test_technical_conflict_resolution_persists_decision_and_evidence(self) -> None:
        task = self._task(role="architect")
        result = self.manager.resolve_technical_conflict(
            self.project["id"], "Authentication boundary", "Use the gateway token verifier and require Security review.",
            options=("local validation", "gateway validation"), arguments=("centralized policy", "reduced duplication"),
            evidence=("security:threat-model-1",), affected_task_ids=(task.id,),
        )
        decisions = list_decisions(project_id=self.project["id"], database_path=self.path)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision_maker"], "engineering_manager")
        self.assertEqual(result.decision_id, decisions[0]["decision_id"])
        self.assertEqual(store.list_messages(project_id=self.project["id"], database_path=self.path)[0]["message_type"], MessageType.DECISION.value)

    def test_blocked_engineer_is_escalated_and_dependency_is_not_bypassed(self) -> None:
        upstream = self._task(role="backend")
        self._running(upstream)
        store.transition(upstream.id, TaskState.FAILED, failure_reason="API contract failure", database_path=self.path)
        dependent = CoordinationTask(project_id=self.project["id"], title="Integration", description="wait for API", role="integration", dependencies=(upstream.id,))
        store.create_task(dependent, database_path=self.path)
        result = self.manager.handle_blocked_engineer(dependent.id, reason="Backend contract is unavailable", reassign_to="integration")
        self.assertEqual(result.state, TaskState.BLOCKED.value)
        self.assertIsNotNone(result.reassignment)
        self.assertEqual(result.reassignment.status, "blocked")
        self.assertEqual(store.get_task(dependent.id, database_path=self.path)["state"], TaskState.BLOCKED.value)
        blocker_messages = store.list_messages(project_id=self.project["id"], topic="engineering_blocker", database_path=self.path)
        self.assertEqual(len(blocker_messages), 2)

    def test_technical_completion_gate_requires_test_and_review_evidence(self) -> None:
        backend = self._task(role="backend", expected_outputs=("api",))
        tester = self._task(role="tester", expected_outputs=("test-result",))
        reviewer = self._task(role="reviewer", expected_outputs=("review",))
        for task in (backend, tester, reviewer):
            self._running(task)
            store.transition(task.id, TaskState.COMPLETED, database_path=self.path)
        set_quality_gate(self.project["id"], "tests_passed", status="passed", evidence=("pytest",), database_path=self.path)
        set_quality_gate(self.project["id"], "review_accepted", status="passed", evidence=("review:accepted",), database_path=self.path)
        readiness = self.manager.technical_readiness(self.project["id"])
        self.assertTrue(readiness.ready)
        self.assertFalse(readiness.missing_evidence)
        failed = self._task(role="tester", title="Regression")
        self._running(failed)
        store.transition(failed.id, TaskState.FAILED, failure_reason="assertion failed", database_path=self.path)
        self.assertFalse(self.manager.technical_readiness(self.project["id"]).ready)


if __name__ == "__main__":
    unittest.main()
