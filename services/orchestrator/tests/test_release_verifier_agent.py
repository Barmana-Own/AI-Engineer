from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract, resolve_role
from app.db import create_project, initialize_database
from app.organization import ReleaseVerifierAgent


class ReleaseVerifierAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Release project", "Verify a release", database_path=self.path)
        self.agent = ReleaseVerifierAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Verify release") -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Independently verify release readiness",
            role="release_verifier",
            expected_outputs=("ReleaseVerification", "ReleaseBlocker"),
            acceptance_criteria=("Every release gate has independent evidence",),
        )
        store.create_task(task, database_path=self.path)
        return task

    @staticmethod
    def _state(label: str, status: str = "completed") -> dict[str, object]:
        return {"status": status, "evidence": [f"{label} evidence"]}

    def _verify(self, task: CoordinationTask, **overrides: object):
        states: dict[str, object] = {
            "requirements": self._state("requirements"),
            "acceptance_criteria": self._state("acceptance criteria"),
            "task_completion": self._state("task completion"),
            "test_results": {"status": "passed", "evidence": ["pytest:tests/test_release.py"]},
            "integration_state": self._state("integration"),
            "review_state": {"status": "accepted", "evidence": ["review:CR-1"]},
            "security_state": {"status": "verified", "evidence": ["security:scan-1"], "findings": []},
            "documentation_state": self._state("documentation"),
            "deployment_readiness": {"status": "ready", "evidence": ["health:staging", "smoke:release"]},
        }
        states.update(overrides)
        return self.agent.verify_release(task.id, **states)

    def test_role_contract_profile_and_alias_are_read_only(self) -> None:
        contract = get_role_contract("release_verifier")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("run_tests", contract.allowed_tools)
        self.assertIn("health_check", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertIn("evidence_assessment", contract.capabilities)
        self.assertEqual(resolve_role("release-verifier"), "release_verifier")
        profile = self.agent.ensure_profile()
        self.assertEqual(profile.role, "release_verifier")
        self.assertEqual(profile.department.value, "OPERATIONS")

    def test_successful_release_verification_requires_and_records_evidence(self) -> None:
        task = self._task()
        verification = self._verify(task)
        self.assertEqual(verification.result, "READY")
        self.assertEqual(verification.status, "READY")
        self.assertFalse(verification.blockers)
        self.assertGreaterEqual(len(verification.evidence), 9)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.RESULT.value, {row["message_type"] for row in messages})

    def test_failed_acceptance_criteria_routes_blocker_to_requirements(self) -> None:
        task = self._task("Acceptance gate")
        verification = self._verify(
            task,
            acceptance_criteria={"status": "failed", "failed_criteria": ["AC-2: audit trail missing"], "evidence": ["acceptance:AC-2"]},
        )
        self.assertEqual(verification.result, "NOT_READY")
        blockers = [item for item in verification.blockers if item.category == "acceptance_criteria"]
        self.assertTrue(blockers)
        self.assertEqual(blockers[0].responsible_role, "requirements")
        self.assertTrue(blockers[0].required_action)
        self.assertTrue(verification.handoff_ids)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn("requirements", {row["recipient_role"] for row in handoffs})

    def test_failed_tests_route_blocker_to_tester(self) -> None:
        task = self._task("Test gate")
        verification = self._verify(
            task,
            test_results={"status": "failed", "evidence": ["pytest:tests/test_api.py::test_auth", "failure:401 expected 200"]},
        )
        self.assertEqual(verification.result, "NOT_READY")
        blocker = next(item for item in verification.blockers if item.category == "test_results")
        self.assertEqual(blocker.responsible_role, "tester")

    def test_pending_review_routes_blocker_to_reviewer(self) -> None:
        task = self._task("Review gate")
        verification = self._verify(task, review_state={"status": "pending", "evidence": ["review:CR-2 awaiting approval"]})
        self.assertEqual(verification.result, "NOT_READY")
        blocker = next(item for item in verification.blockers if item.category == "review_state")
        self.assertEqual(blocker.responsible_role, "reviewer")

    def test_security_blocker_prevents_release(self) -> None:
        task = self._task("Security gate")
        verification = self._verify(
            task,
            security_state={
                "status": "verified",
                "evidence": ["security:scan-3"],
                "findings": [{"id": "SEC-7", "severity": "critical", "status": "open", "evidence": ["auth bypass finding"]}],
            },
        )
        self.assertEqual(verification.result, "NOT_READY")
        blocker = next(item for item in verification.blockers if item.category == "security_state" and "security finding" in item.reason)
        self.assertEqual(blocker.responsible_role, "security")
        self.assertEqual(blocker.severity, "critical")

    def test_status_labels_without_evidence_are_not_accepted(self) -> None:
        task = self._task("Evidence gate")
        states = {
            "requirements": {"status": "completed"},
            "acceptance_criteria": {"status": "passed"},
            "task_completion": {"status": "completed"},
            "test_results": {"status": "passed"},
            "integration_state": {"status": "complete"},
            "review_state": {"status": "accepted"},
            "security_state": {"status": "verified", "findings": []},
            "documentation_state": {"status": "complete"},
            "deployment_readiness": {"status": "ready"},
        }
        verification = self._verify(task, **states)
        self.assertEqual(verification.result, "NOT_READY")
        self.assertTrue(any("independent evidence" in item.reason for item in verification.blockers))

    def test_accepted_risk_is_explicitly_reported(self) -> None:
        task = self._task("Accepted risk gate")
        verification = self.agent.verify_release(
            task.id,
            requirements=self._state("requirements"),
            acceptance_criteria=self._state("acceptance criteria"),
            task_completion=self._state("task completion"),
            test_results={"status": "passed", "evidence": ["pytest:all"]},
            integration_state=self._state("integration"),
            review_state={"status": "accepted", "evidence": ["review:accepted"]},
            security_state={"status": "verified", "evidence": ["security:scan"], "findings": []},
            documentation_state=self._state("documentation"),
            deployment_readiness={"status": "ready", "evidence": ["health:staging"]},
            accepted_risks=({"risk_id": "RISK-1", "status": "accepted", "approved_by": "owner-policy", "evidence": ["decision:DR-1"]},),
        )
        self.assertEqual(verification.result, "READY_WITH_ACCEPTED_RISKS")
        self.assertEqual(verification.accepted_risks, ("RISK-1",))


if __name__ == "__main__":
    unittest.main()
