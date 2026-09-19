from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, TaskState, WritePermission
from app.coordination.project_management import list_work_queue
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import BackendEngineerAgent


class BackendEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Backend project", "Backend execution", database_path=self.path)
        self.backend = BackendEngineerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Implement API", scope: tuple[str, ...] = ("services/api.py",)) -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Implement backend behavior",
            role="backend",
            scope=scope,
            writer=True,
            expected_outputs=("code_changes", "tests"),
            acceptance_criteria=("API contract is preserved",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_role_contract_has_scoped_backend_tools_and_no_global_rollback(self) -> None:
        contract = get_role_contract("backend")
        self.assertEqual(contract.write_permission, WritePermission.SCOPED)
        self.assertIn("read_file", contract.allowed_tools)
        self.assertIn("write_file", contract.allowed_tools)
        self.assertIn("replace_text", contract.allowed_tools)
        self.assertIn("run_tests", contract.allowed_tools)
        self.assertIn("checkpoint", contract.allowed_tools)
        self.assertNotIn("git_rollback", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("assigned_scope", "assigned_backend_scope", "assigned_migrations"))
        profile = self.backend.ensure_profile()
        self.assertEqual(profile.role, "backend")
        self.assertEqual(profile.write_permission, WritePermission.SCOPED.value)

    def test_prepare_requires_inspection_and_persists_backend_plan(self) -> None:
        task = self._task()
        with self.assertRaises(ValueError):
            self.backend.prepare(task.id, requirements=("FR-001",))
        plan = self.backend.prepare(
            task.id,
            requirements=("FR-001",),
            architecture_refs=("decision:gateway-boundary",),
            api_contracts=({"method": "GET", "path": "/health"},),
            security_requirements=("validate authorization",),
            migration_plan=("add idempotent migration",),
            acceptance_criteria=("returns validated response",),
            test_plan=("contract test",),
            inspection_evidence=("inspected app/routes.py and app/repositories.py",),
        )
        self.assertEqual(plan.scope, ("services/api.py",))
        self.assertEqual(plan.migration_plan, ("add idempotent migration",))
        self.assertIsNotNone(plan.message_id)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="backend_plan", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.STATUS.value)

    def test_claim_prevents_conflicting_writers_and_releases_lock(self) -> None:
        first = self._task("First API", ("services/api.py",))
        second = self._task("Second API", ("services/api.py",))
        claimed = self.backend.claim(first.id)
        self.assertTrue(claimed.lock_acquired)
        self.assertEqual(claimed.state, TaskState.RUNNING.value)
        blocked = self.backend.claim(second.id)
        self.assertFalse(blocked.lock_acquired)
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(store.get_task(second.id, database_path=self.path)["state"], TaskState.BLOCKED.value)
        result = self.backend.record_result(
            first.id,
            code_changes=("Added validated health endpoint",),
            files_changed=("services/api.py",),
            tests=("backend contract test passed",),
        )
        self.assertEqual(result.status, TaskState.REVIEW.value)
        retry = self.backend.claim(second.id)
        self.assertTrue(retry.lock_acquired)
        self.assertEqual(retry.state, TaskState.RUNNING.value)

    def test_result_records_migrations_tests_and_handoffs_to_integration_and_qa(self) -> None:
        task = self._task("Persistence API", ("services/repository.py", "migrations/001_add_status.sql"))
        self.backend.claim(task.id)
        result = self.backend.record_result(
            task.id,
            code_changes=("Added transactional repository method",),
            migration_changes=("Created idempotent status migration",),
            files_changed=("services/repository.py", "migrations/001_add_status.sql"),
            tests=("repository transaction test passed",),
            technical_notes=("Uses parameterized queries and existing connection helper.",),
            verification=("migration applied to isolated SQLite database",),
        )
        self.assertEqual(result.status, TaskState.REVIEW.value)
        self.assertEqual(len(result.handoff_ids), 2)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual({row["recipient_role"] for row in handoffs}, {"integration", "tester"})
        self.assertTrue(store.resources_available(("services/repository.py",), task.id, database_path=self.path))
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.RESULT.value, {row["message_type"] for row in messages})
        self.assertEqual(len([row for row in messages if row["message_type"] == MessageType.HANDOFF.value]), 2)
        queue = [row for row in list_work_queue(project_id=self.project["id"], database_path=self.path) if row["task_id"] == task.id]
        self.assertEqual({row["agent_id"] for row in queue}, {"integration", "tester"})


if __name__ == "__main__":
    unittest.main()
