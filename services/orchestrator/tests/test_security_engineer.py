from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract, resolve_role
from app.db import create_project, initialize_database
from app.organization import SecurityEngineerAgent


class SecurityEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project(
            "Security project",
            "Evidence-based security review",
            database_path=self.path,
        )
        self.security = SecurityEngineerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Review authentication change", *, implementation_role: str = "backend", assigned_agent: str | None = None) -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Review security-sensitive changes before release",
            role="security",
            assigned_agent=assigned_agent,
            inputs={"implementation_role": implementation_role},
            expected_outputs=("SecurityReview", "SecurityFinding"),
            acceptance_criteria=("No unresolved high or critical finding remains",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_security_review_contract_is_read_only_and_evidence_based(self) -> None:
        contract = get_role_contract("security")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("diff", contract.allowed_tools)
        self.assertIn("security_scan", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertIn("threat_modeling", contract.capabilities)
        self.assertIn("escalations", contract.performance_signals)
        self.assertEqual(resolve_role("security-engineer"), "security")
        profile = self.security.ensure_profile()
        self.assertEqual(profile.role, "security")
        self.assertEqual(profile.department.value, "SECURITY")

    def test_critical_finding_blocks_release_and_routes_revision(self) -> None:
        task = self._task()
        review = self.security.review_changes(
            task.id,
            outcome="APPROVED",
            reviewed_role="backend",
            findings=(
                {
                    "title": "Authentication bypass",
                    "severity": "CRITICAL",
                    "description": "A missing authorization check allows cross-project access.",
                    "remediation": "Enforce ownership authorization at the service boundary.",
                    "evidence": ({"file": "services/auth.py", "test": "pytest:test_authz", "requirement": "NFR-SEC-1"},),
                },
            ),
            changed_files=("services/auth.py",),
            diffs=("diff:missing-authz-check",),
        )

        self.assertEqual(review.outcome, "BLOCKED")
        self.assertTrue(review.release_blocked)
        self.assertEqual(review.findings[0].severity, "CRITICAL")
        self.assertTrue(review.findings[0].blocks_release)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual(handoffs[-1]["recipient_role"], "backend")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        message_types = {row["message_type"] for row in messages}
        self.assertIn(MessageType.BLOCKER.value, message_types)
        self.assertIn(MessageType.DECISION.value, message_types)

    def test_high_risk_decision_escalates_to_supervisor(self) -> None:
        task = self._task("Escalate production exposure")
        review = self.security.escalate_decision(
            task.id,
            summary="Production storage is publicly reachable.",
            severity="HIGH",
            evidence=({"file": "deploy/storage.yaml", "decision": "ADR-SEC-1"},),
        )

        self.assertEqual(review.outcome, "BLOCKED")
        self.assertTrue(review.release_blocked)
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        escalation = [row for row in messages if row["topic"] == "security_decision_escalation"]
        self.assertTrue(escalation)
        self.assertEqual(escalation[-1]["recipient_role"], "supervisor")

    def test_owner_risk_acceptance_requires_authorized_policy_reference(self) -> None:
        task = self._task("Require owner policy")
        finding = {"title": "Weak cookie policy", "severity": "HIGH", "evidence": ({"file": "app/config.py"},)}
        with self.assertRaises(PermissionError):
            self.security.review_changes(
                task.id,
                findings=(finding,),
                evidence=({"file": "app/config.py"},),
                outcome="ACCEPTED_RISK",
                owner_approval=True,
            )

        accepted = self.security.review_changes(
            task.id,
            findings=(finding,),
            evidence=({"file": "app/config.py", "decision": "OWNER-RISK-42"},),
            outcome="ACCEPTED_RISK",
            owner_approval=True,
            authorization_reference="OWNER-RISK-42",
        )
        self.assertEqual(accepted.outcome, "ACCEPTED_RISK")
        self.assertFalse(accepted.release_blocked)

    def test_security_re_review_can_clear_a_fixed_finding(self) -> None:
        task = self._task("Re-review authorization fix")
        first = self.security.review_changes(
            task.id,
            findings=({"title": "Missing authorization", "severity": "HIGH", "evidence": ({"file": "services/api.py"},)},),
            evidence=({"file": "services/api.py", "test": "pytest:test_authz"},),
            outcome="BLOCKED",
            reviewed_role="backend",
        )
        second = self.security.re_review(
            task.id,
            previous_review_id=first.review_id,
            evidence=({"file": "services/api.py", "diff": "diff:authorization-fix", "test": "pytest:test_authz_passed"},),
            reviewed_role="backend",
        )

        self.assertEqual(second.outcome, "APPROVED")
        self.assertFalse(second.release_blocked)
        self.assertEqual(second.re_review_of, first.review_id)


if __name__ == "__main__":
    unittest.main()


