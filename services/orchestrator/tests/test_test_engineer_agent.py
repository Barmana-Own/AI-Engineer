from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import TestEngineerAgent


class TestEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("QA project", "Independent verification", database_path=self.path)
        self.tester = TestEngineerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Verify API behavior") -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Verify implementation against acceptance criteria",
            role="tester",
            scope=("tests/test_api.py",),
            writer=False,
            expected_outputs=("DefectReport", "RegressionVerification"),
            acceptance_criteria=("API returns valid response",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_plan_and_failure_reporting_are_independent_and_read_only(self) -> None:
        contract = get_role_contract("tester")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("run_tests", contract.allowed_tools)
        self.assertNotIn("write_file", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertIn("debugger", contract.handoff_targets)
        profile = self.tester.ensure_profile()
        self.assertEqual(profile.role, "tester")
        self.assertEqual(profile.department.value, "QUALITY")
        task = self._task()
        plan = self.tester.create_test_plan(
            task.id,
            acceptance_criteria=("API returns valid response",),
            test_cases=({"name": "test_api_response", "command": "pytest tests/test_api.py"},),
            inspection_evidence=("inspection:api-route",),
        )
        self.assertEqual(plan.status, "planned")
        defect = self.tester.record_failure(
            task.id,
            test_name="test_api_response",
            reproduction_steps=("start service", "GET /v1/projects", "assert status is 200"),
            expected_behavior="The endpoint returns HTTP 200 with an items array.",
            actual_behavior="The endpoint returns HTTP 500.",
            evidence=("pytest:failed:test_api_response", "trace:request-1"),
            affected_files=("services/api.py",),
            owner_role="debugger",
        )
        self.assertEqual(defect.owner_role, "debugger")
        self.assertTrue(defect.handoff_id)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual(handoffs[0]["recipient_role"], "debugger")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.BLOCKER.value, {row["message_type"] for row in messages})
        self.assertIn(MessageType.HANDOFF.value, {row["message_type"] for row in messages})

    def test_repair_loop_requires_rerun_evidence_and_records_result(self) -> None:
        task = self._task()
        defect = self.tester.record_failure(
            task.id,
            test_name="test_repair",
            reproduction_steps=("run test",),
            expected_behavior="The test passes.",
            actual_behavior="The test fails.",
            evidence=("pytest:failure",),
        )
        with self.assertRaises(ValueError):
            self.tester.verify_repair(task.id, defect.defect_id, passed=True, tests=(), evidence=("trace:rerun",))
        loop = self.tester.verify_repair(
            task.id,
            defect.defect_id,
            passed=True,
            tests=("pytest tests/test_api.py::test_repair",),
            evidence=("pytest:passed:repair",),
        )
        self.assertTrue(loop.passed)
        self.assertEqual(loop.status, "verified")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="repair_verification", database_path=self.path)
        self.assertEqual(messages[-1]["message_type"], MessageType.RESULT.value)

    def test_regression_verification_records_failure_and_success(self) -> None:
        task = self._task("Regression suite")
        with self.assertRaises(ValueError):
            self.tester.verify_regression(task.id, passed=True, tests=("pytest",), evidence=())
        failed = self.tester.verify_regression(
            task.id,
            passed=False,
            tests=("pytest tests/test_regression.py",),
            evidence=("pytest:failed:regression",),
        )
        self.assertEqual(failed.status, "failed")
        passed = self.tester.verify_regression(
            task.id,
            passed=True,
            tests=("pytest tests/test_regression.py",),
            evidence=("pytest:passed:regression",),
        )
        self.assertEqual(passed.status, "passed")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="regression_verification", database_path=self.path)
        self.assertEqual([row["message_type"] for row in messages], [MessageType.BLOCKER.value, MessageType.RESULT.value])

    def test_acceptance_criteria_verification_routes_failed_criteria(self) -> None:
        task = self._task("Acceptance gate")
        verification = self.tester.verify_acceptance_criteria(
            task.id,
            {"AC-1": True, "AC-2": False},
            evidence=("acceptance:manual-check", "acceptance:api-test"),
        )
        self.assertEqual(verification.passed_criteria, ("AC-1",))
        self.assertEqual(verification.failed_criteria, ("AC-2",))
        self.assertEqual(verification.status, "failed")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, topic="acceptance_verification", database_path=self.path)
        self.assertEqual(messages[0]["message_type"], MessageType.BLOCKER.value)


if __name__ == "__main__":
    unittest.main()



