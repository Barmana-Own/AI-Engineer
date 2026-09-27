from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import CodeReviewerAgent


class CodeReviewerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project(
            "Reviewer project",
            "Independent evidence-based review",
            database_path=self.path,
        )
        self.reviewer = CodeReviewerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(
        self,
        title: str = "Review backend change",
        *,
        implementation_role: str = "backend",
        assigned_agent: str | None = None,
    ) -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Independently review an implementation before completion",
            role="reviewer",
            assigned_agent=assigned_agent,
            inputs={"implementation_role": implementation_role},
            expected_outputs=("CodeReview", "ReviewEvidence"),
            acceptance_criteria=("Every conclusion references concrete evidence",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_independent_approval_is_read_only_and_evidence_based(self) -> None:
        contract = get_role_contract("reviewer")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("diff", contract.allowed_tools)
        self.assertNotIn("write_file", contract.allowed_tools)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertIn("self_review_attempts", contract.performance_signals)
        profile = self.reviewer.ensure_profile()
        self.assertEqual(profile.role, "reviewer")

        task = self._task()
        review = self.reviewer.review_changes(
            task.id,
            outcome="APPROVED",
            reviewed_role="backend",
            changed_files=("services/api.py",),
            diffs=("diff:api-contract",),
            tests=("pytest:test_api",),
            requirements=("REQ-API-1",),
            decisions=("ADR-1",),
        )

        self.assertEqual(review.outcome, "APPROVED")
        self.assertIsNone(review.handoff_id)
        self.assertEqual(review.reviewed_role, "backend")
        fields = {field for evidence in review.evidence for field in evidence.as_dict()}
        self.assertTrue({"file", "diff", "test", "requirement", "decision"}.issubset(fields))
        messages = store.list_messages(
            project_id=self.project["id"], task_id=task.id, topic="code_review", database_path=self.path
        )
        self.assertEqual(messages[-1]["message_type"], MessageType.REVIEW.value)

    def test_self_review_is_rejected_before_approval(self) -> None:
        task = self._task("Reject reviewer self approval")
        with self.assertRaises(PermissionError):
            self.reviewer.review_changes(
                task.id,
                outcome="APPROVED",
                reviewed_role="reviewer",
                evidence=({"file": "app/organization/reviewer.py"},),
            )

        implementation_task = self._task(
            "Reject reviewer-authored change",
            assigned_agent="employee-reviewer",
        )
        with self.assertRaises(PermissionError):
            self.reviewer.review_changes(
                implementation_task.id,
                outcome="APPROVED",
                reviewed_role="backend",
                evidence=({"diff": "diff:self-authored"},),
            )

    def test_revision_request_creates_evidence_handoff_and_message(self) -> None:
        task = self._task()
        review = self.reviewer.review_changes(
            task.id,
            outcome="REVISION_REQUIRED",
            reviewed_role="backend",
            findings=(
                {
                    "summary": "Missing request validation",
                    "severity": "high",
                    "recommendation": "Validate the request schema before persistence",
                    "evidence": ({"file": "services/api.py", "test": "pytest:test_validation", "requirement": "REQ-1"},),
                },
            ),
            changed_files=("services/api.py",),
            diffs=("diff:missing-validation",),
        )

        self.assertEqual(review.outcome, "REVISION_REQUIRED")
        self.assertTrue(review.handoff_id)
        self.assertTrue(review.message_id)
        handoffs = store.list_handoffs(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertEqual(handoffs[-1]["recipient_role"], "backend")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        message_types = {row["message_type"] for row in messages}
        self.assertIn(MessageType.REVIEW.value, message_types)
        self.assertIn(MessageType.REVISION_REQUEST.value, message_types)

    def test_approval_with_notes_preserves_review_evidence(self) -> None:
        task = self._task("Approve with notes")
        review = self.reviewer.approve(
            task.id,
            notes=("Contract and regression coverage are sufficient.",),
            reviewed_role="frontend",
            evidence=({"file": "apps/control-center/src/api.ts", "test": "npm test", "decision": "ADR-2"},),
        )

        self.assertEqual(review.outcome, "APPROVED_WITH_NOTES")
        self.assertEqual(len(review.findings), 1)
        self.assertIn("Contract and regression coverage are sufficient.", review.findings[0].summary)
        evidence = review.evidence[0].as_dict()
        self.assertEqual(evidence["file"], "apps/control-center/src/api.ts")
        self.assertEqual(evidence["test"], "npm test")
        self.assertEqual(evidence["decision"], "ADR-2")


if __name__ == "__main__":
    unittest.main()




