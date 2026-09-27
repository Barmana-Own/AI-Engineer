from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.memory.store import MemoryStore
from app.organization import DebuggerAgent


class DebuggerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Debugger project", "Bounded failure repair", database_path=self.path)
        self.debugger = DebuggerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Repair failing API test") -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Reproduce, diagnose and repair a confirmed failure",
            role="debugger",
            scope=("services/api.py", "tests/test_api.py"),
            writer=True,
            expected_outputs=("RootCauseRecord", "RepairResult"),
            acceptance_criteria=("Regression test passes after the minimal repair",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_failure_reproduction_records_evidence_and_contract(self) -> None:
        contract = get_role_contract("debugger")
        self.assertEqual(contract.write_permission, WritePermission.SCOPED)
        self.assertIn("write_file", contract.allowed_tools)
        self.assertIn("checkpoint", contract.allowed_tools)
        self.assertIn("tester", contract.handoff_targets)
        self.assertIn("failure_reproduction", contract.capabilities)
        profile = self.debugger.ensure_profile()
        self.assertEqual(profile.role, "debugger")
        task = self._task()
        reproduction = self.debugger.reproduce_failure(
            task.id,
            defect_id="defect-api-1",
            reproduction_steps=("start service", "GET /v1/projects", "assert status is 200"),
            expected_behavior="The endpoint returns HTTP 200.",
            actual_behavior="The endpoint returns HTTP 500.",
            logs=("request failed with database timeout",),
            stack_trace="TimeoutError: database did not respond",
            evidence=("pytest:failed:test_projects", "trace:request-1"),
        )
        self.assertEqual(reproduction.status, "reproduced")
        self.assertEqual(reproduction.defect_id, "defect-api-1")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="failure_reproduction", database_path=self.path)
        self.assertEqual(messages[0]["message_type"], MessageType.EVIDENCE.value)

    def test_root_cause_record_creates_failure_memory_candidate(self) -> None:
        task = self._task("Diagnose timeout")
        root = self.debugger.record_root_cause(
            task.id,
            defect_id="defect-timeout",
            root_cause="The repository call omitted a bounded timeout and exhausted the request worker.",
            contributing_factors=("No timeout at the database boundary",),
            affected_scope=("services/repository.py",),
            evidence=("stack:timeout", "inspection:repository-call"),
            confidence="high",
        )
        self.assertEqual(root.status, "diagnosed")
        self.assertTrue(root.memory_id)
        memory = MemoryStore(self.path).get(root.memory_id)
        self.assertEqual(memory["memory_type"], "failure")
        self.assertEqual(memory["lifecycle"], "candidate")
        patterns = MemoryStore(self.path).failure_patterns(project_id=self.project["id"], query="timeout")
        self.assertEqual(len(patterns), 1)

    def test_authorized_repair_routes_to_tester_and_requires_permission(self) -> None:
        task = self._task("Repair response failure")
        root = self.debugger.record_root_cause(
            task.id,
            defect_id="defect-response",
            root_cause="The serializer omitted the required items field.",
            evidence=("pytest:response-contract",),
        )
        with self.assertRaises(PermissionError):
            self.debugger.repair_failure(
                task.id,
                defect_id="defect-response",
                repair_summary="Add the missing response field",
                changed_files=("services/api.py",),
                regression_tests=("pytest tests/test_api.py::test_response",),
                evidence=("review:repair-plan",),
                root_cause_id=root.root_cause_id,
            )
        repair = self.debugger.repair_failure(
            task.id,
            defect_id="defect-response",
            repair_summary="Add the missing response field at the serializer boundary.",
            changed_files=("services/api.py",),
            regression_tests=("pytest tests/test_api.py::test_response",),
            evidence=("diff:serializer-field",),
            authorized=True,
            root_cause_id=root.root_cause_id,
            memory_id=root.memory_id,
        )
        self.assertEqual(repair.status, "ready_for_test")
        self.assertTrue(repair.handoff_id)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual(handoffs[-1]["recipient_role"], "tester")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.RESULT.value, {row["message_type"] for row in messages})
        self.assertIn(MessageType.HANDOFF.value, {row["message_type"] for row in messages})

    def test_failure_memory_is_promoted_only_with_verification_evidence(self) -> None:
        task = self._task("Capture recurring failure")
        memory = self.debugger.create_failure_memory(
            task.id,
            title="SQLite migration ordering failure",
            root_cause="A migration referenced a table created by a later migration.",
            successful_fix="Move the dependent index into the later migration.",
            evidence=("migration-test:failed",),
        )
        self.assertEqual(memory.lifecycle, "candidate")
        promoted = self.debugger.promote_failure_memory(
            memory.memory_id,
            evidence=("migration-test:passed", "review:accepted"),
        )
        self.assertEqual(promoted.lifecycle, "validated")
        retrieved = MemoryStore(self.path).retrieve(project_id=self.project["id"], query="SQLite migration ordering")
        self.assertEqual(retrieved[0]["id"], memory.memory_id)


if __name__ == "__main__":
    unittest.main()
