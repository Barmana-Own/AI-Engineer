from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, TaskState, WritePermission
from app.coordination.project_management import list_work_queue
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import FrontendEngineerAgent


class FrontendEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Frontend project", "Frontend execution", database_path=self.path)
        self.frontend = FrontendEngineerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Implement client", scope: tuple[str, ...] = ("apps/control-center/src/App.tsx",)) -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Implement frontend behavior",
            role="frontend",
            scope=scope,
            writer=True,
            expected_outputs=("code_changes", "tests"),
            acceptance_criteria=("UX and API contracts are preserved",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_role_contract_has_scoped_frontend_tools_and_handoffs(self) -> None:
        contract = get_role_contract("frontend")
        self.assertEqual(contract.write_permission, WritePermission.SCOPED)
        self.assertIn("write_file", contract.allowed_tools)
        self.assertIn("replace_text", contract.allowed_tools)
        self.assertIn("run_tests", contract.allowed_tools)
        self.assertIn("checkpoint", contract.allowed_tools)
        self.assertNotIn("git_rollback", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("assigned_scope", "assigned_frontend_scope"))
        self.assertEqual(set(contract.handoff_targets), {"integration", "tester"})
        profile = self.frontend.ensure_profile()
        self.assertEqual(profile.role, "frontend")
        self.assertEqual(profile.write_permission, WritePermission.SCOPED.value)

    def test_assignment_consumes_design_handoff_and_persists_plan(self) -> None:
        task = self._task()
        with self.assertRaises(ValueError):
            self.frontend.prepare(task.id, inspection_evidence=("inspected App.tsx",))
        plan = self.frontend.prepare(
            task.id,
            ux_spec_refs=("design:ux-1",),
            architecture_refs=("decision:route-boundary",),
            api_contracts=({"method": "GET", "path": "/v1/projects"},),
            routing=("/projects",),
            state_management=("server query cache",),
            forms=("inline validation",),
            accessibility=("keyboard focus order",),
            responsive_rules=("stack controls below 640px",),
            inspection_evidence=("inspected App.tsx and api/client.py",),
        )
        self.assertEqual(plan.ux_spec_refs, ("design:ux-1",))
        self.assertEqual(plan.api_contracts[0]["path"], "/v1/projects")
        self.assertIsNotNone(plan.message_id)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="frontend_plan", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.STATUS.value)

    def test_backend_api_clarification_request_is_structured(self) -> None:
        task = self._task()
        request = self.frontend.request_backend_clarification(
            task.id,
            "Project status response",
            "Which fields are stable for the client?",
            expected_contract="GET /v1/projects -> ProjectSummary",
            evidence=("api-contract:unknown",),
        )
        self.assertEqual(request.recipient_role, "backend")
        self.assertEqual(request.status, "open")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="frontend_api_question", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.QUESTION.value)
        self.assertEqual(messages[0]["recipient_role"], "backend")

    def test_integration_issue_and_handoffs_are_persisted(self) -> None:
        task = self._task("Client integration")
        self.frontend.claim(task.id)
        issue = self.frontend.raise_integration_issue(
            task.id,
            "Response contract mismatch",
            "Client expects a projects array",
            "Backend currently returns an object without projects",
            evidence=("contract-test:failed",),
        )
        self.assertEqual(issue.status, "open")
        result = self.frontend.record_result(
            task.id,
            ux_spec_refs=("design:ux-1",),
            api_contracts_used=({"method": "GET", "path": "/v1/projects"},),
            code_changes=("Added responsive project list and error state",),
            files_changed=("apps/control-center/src/App.tsx",),
            tests=("frontend component test passed",),
            verification=("accessibility smoke check passed",),
        )
        self.assertEqual(result.status, TaskState.REVIEW.value)
        self.assertEqual(len(result.handoff_ids), 2)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual({row["recipient_role"] for row in handoffs}, {"integration", "tester"})
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.BLOCKER.value, {row["message_type"] for row in messages})
        self.assertIn(MessageType.RESULT.value, {row["message_type"] for row in messages})
        self.assertEqual(len([row for row in messages if row["message_type"] == MessageType.HANDOFF.value]), 2)
        queue = [row for row in list_work_queue(project_id=self.project["id"], database_path=self.path) if row["task_id"] == task.id]
        self.assertEqual({row["agent_id"] for row in queue}, {"integration", "tester"})


if __name__ == "__main__":
    unittest.main()
