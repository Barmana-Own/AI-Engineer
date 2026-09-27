from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import IntegrationEngineerAgent


class IntegrationEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Integration project", "Cross-component verification", database_path=self.path)
        self.integration = IntegrationEngineerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Verify API integration") -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Verify independent components together",
            role="integration",
            scope=("services/api.py", "apps/control-center/src/api.ts"),
            writer=False,
            expected_outputs=("IntegrationReport",),
            acceptance_criteria=("API and workflow contracts agree",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_api_mismatch_creates_owner_revision_request(self) -> None:
        contract = get_role_contract("integration")
        self.assertEqual(contract.write_permission, WritePermission.SCOPED)
        self.assertIn("run_tests", contract.allowed_tools)
        self.assertNotIn("write_file", contract.allowed_tools)
        self.assertIn("assigned_scope", contract.writable_scope)
        task = self._task()
        report = self.integration.validate_contracts(
            task.id,
            {"method": "GET", "path": "/v1/projects", "response_schema": {"items": "array"}},
            {"method": "GET", "path": "/v1/projects", "response_schema": {"items": "object"}},
            owner_role="backend",
            evidence=("contract-test:response-shape",),
        )
        self.assertEqual(report.status, "failed")
        self.assertEqual(len(report.contract_mismatches), 1)
        self.assertEqual(report.contract_mismatches[0].owner_role, "backend")
        self.assertEqual(len(report.revision_request_ids), 1)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn("backend", {row["recipient_role"] for row in handoffs})
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.BLOCKER.value, {row["message_type"] for row in messages})
        self.assertIn(MessageType.REVISION_REQUEST.value, {row["message_type"] for row in messages})

    def test_cross_agent_revision_request_can_target_frontend(self) -> None:
        task = self._task("Route revision")
        request = self.integration.request_revision(
            task.id,
            {"mismatch_id": "mismatch-1", "boundary": "frontend-backend-api", "field": "path", "reason": "Frontend path differs from the published backend route"},
            "frontend",
            requested_changes=("Update the client route to the published API path",),
            evidence=("api-contract:route-review",),
        )
        self.assertEqual(request.owner_role, "frontend")
        self.assertEqual(request.mismatch_id, "mismatch-1")
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual(handoffs[0]["recipient_role"], "frontend")

    def test_integration_success_requires_independent_evidence(self) -> None:
        task = self._task("Successful workflow")
        with self.assertRaises(ValueError):
            self.integration.record_success(task.id, checks=("API contract",))
        success = self.integration.record_success(
            task.id,
            checks=("frontend/backend response contract", "configuration compatibility"),
            tests=("full integration test passed",),
            evidence=("trace:workflow-1",),
        )
        self.assertEqual(success.status, "passed")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="integration_success", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.RESULT.value)

    def test_integration_failure_is_persisted_and_routes_repair(self) -> None:
        task = self._task("Failed workflow")
        failure = self.integration.record_failure(
            task.id,
            boundary="frontend-backend-api",
            reason="Backend response omitted the required project identifier",
            owner_role="backend",
            evidence=("integration-test:missing-id",),
            tests=("FAIL test_project_response_contract",),
        )
        self.assertEqual(failure.status, "open")
        self.assertEqual(failure.owner_role, "backend")
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual({row["recipient_role"] for row in handoffs}, {"backend"})
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.BLOCKER.value, {row["message_type"] for row in messages})
        self.assertIn(MessageType.REVISION_REQUEST.value, {row["message_type"] for row in messages})


if __name__ == "__main__":
    unittest.main()
