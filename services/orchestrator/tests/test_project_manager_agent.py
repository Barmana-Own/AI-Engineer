from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, TaskState, WritePermission
from app.organization import ProjectManagerAgent
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database


class ProjectManagerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("PM project", "Delivery coordination", database_path=self.path)
        self.other = create_project("Other project", "Isolation", database_path=self.path)
        self.manager = ProjectManagerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def test_role_contract_and_profile_are_least_privilege(self) -> None:
        contract = get_role_contract("project_manager")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("milestone planning", contract.capabilities)
        self.assertIn("status reporting", contract.capabilities)
        profile = self.manager.ensure_profile()
        self.assertEqual(profile.role, "project_manager")
        self.assertEqual(profile.write_permission, WritePermission.READ_ONLY.value)

    def test_milestone_creation_creates_dag_tasks_and_queue_entries(self) -> None:
        plan = self.manager.create_milestone(
            self.project["id"],
            "MVP delivery",
            deliverables=(
                {"title": "API", "role": "backend", "writer": True, "scope": ("services/api",)},
                {"title": "Tests", "role": "tester", "dependencies": ("API",), "acceptance_criteria": ("pytest passes",)},
            ),
        )
        self.assertEqual(plan.project_id, self.project["id"])
        self.assertEqual(len(plan.deliverables), 2)
        parent = store.get_task(plan.task_id, database_path=self.path)
        self.assertEqual(parent["role"], "project_manager")
        children = [store.get_task(item.task_id, database_path=self.path) for item in plan.deliverables]
        self.assertEqual({item["role"] for item in children}, {"backend", "tester"})
        self.assertEqual(children[1]["dependencies"], [children[0]["id"]])
        self.assertTrue(plan.scheduled_queue_ids)

    def test_dependency_management_is_project_local_and_restart_safe(self) -> None:
        upstream = CoordinationTask(project_id=self.project["id"], title="requirements", description="requirements", role="requirements")
        downstream = CoordinationTask(project_id=self.project["id"], title="plan", description="plan", role="planner")
        foreign = CoordinationTask(project_id=self.other["id"], title="foreign", description="foreign", role="planner")
        for task in (upstream, downstream, foreign):
            store.create_task(task, database_path=self.path)
        updated = self.manager.add_dependency(downstream.id, upstream.id)
        self.assertEqual(updated["dependencies"], [upstream.id])
        self.assertEqual(self.manager.dependencies(downstream.id)[0]["depends_on_task_id"], upstream.id)
        with self.assertRaises(ValueError):
            self.manager.add_dependency(downstream.id, foreign.id)

    def test_blocked_task_detection_reports_failed_dependency(self) -> None:
        upstream = CoordinationTask(project_id=self.project["id"], title="build", description="build", role="backend")
        store.create_task(upstream, database_path=self.path)
        store.transition(upstream.id, TaskState.READY, database_path=self.path)
        store.transition(upstream.id, TaskState.ASSIGNED, database_path=self.path)
        store.transition(upstream.id, TaskState.RUNNING, database_path=self.path)
        store.transition(upstream.id, TaskState.FAILED, failure_reason="compiler failure", database_path=self.path)
        downstream = CoordinationTask(project_id=self.project["id"], title="verify", description="verify", role="tester", dependencies=(upstream.id,))
        store.create_task(downstream, database_path=self.path)
        blocked = self.manager.detect_blocked_tasks(self.project["id"])
        self.assertEqual(blocked[0]["task_id"], downstream.id)
        self.assertEqual(blocked[0]["reason"], "dependency_failed")
        self.assertEqual(store.get_task(downstream.id, database_path=self.path)["state"], TaskState.BLOCKED.value)

    def test_status_report_tracks_completed_current_pending_and_risks(self) -> None:
        task = CoordinationTask(project_id=self.project["id"], title="deliver", description="deliver", role="implementer")
        store.create_task(task, database_path=self.path)
        store.transition(task.id, TaskState.READY, database_path=self.path)
        store.transition(task.id, TaskState.ASSIGNED, database_path=self.path)
        store.transition(task.id, TaskState.RUNNING, database_path=self.path)
        store.transition(task.id, TaskState.COMPLETED, database_path=self.path)
        report = self.manager.status_report(self.project["id"])
        self.assertEqual(report.task_counts[TaskState.COMPLETED.value], 1)
        self.assertEqual(report.completed_work[0]["task_id"], task.id)
        self.assertIn("Review completion evidence", " ".join(report.next_actions))

    def test_scope_escalation_persists_owner_gate_without_commitment(self) -> None:
        escalation = self.manager.escalate_scope(
            self.project["id"],
            reason="Client added a security-sensitive integration",
            requested_change="Add OAuth provider and security review",
        )
        self.assertTrue(escalation["requires_human_owner_approval"])
        self.assertFalse(escalation["commitment_made"])
        messages = self.manager.bus.relevant(project_id=self.project["id"], topic="scope_escalation")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.BLOCKER.value)
        self.assertEqual(messages[0]["recipient_role"], "company_director")


if __name__ == "__main__":
    unittest.main()
