from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import CoordinationTask, MessageType, WritePermission
from app.coordination.roles import get_role_contract, resolve_role
from app.db import create_project, initialize_database
from app.organization import DocumentationEngineerAgent, DocumentationEvidence


class DocumentationEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Documentation project", "Keep docs synchronized", database_path=self.path)
        self.agent = DocumentationEngineerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _task(self, title: str = "Synchronize documentation") -> CoordinationTask:
        task = CoordinationTask(
            project_id=self.project["id"],
            title=title,
            description="Inspect source and update documentation",
            role="docs",
            expected_outputs=("DocumentationUpdate", "DocumentationDriftReport"),
            acceptance_criteria=("Implemented claims include source evidence and verification",),
        )
        store.create_task(task, database_path=self.path)
        return task

    def test_role_contract_profile_and_alias_are_scoped(self) -> None:
        contract = get_role_contract("docs")
        self.assertEqual(contract.write_permission, WritePermission.SCOPED)
        self.assertIn("write_file", contract.allowed_tools)
        self.assertIn("documentation_drift_detection", contract.capabilities)
        self.assertIn("assigned_scope", contract.writable_scope)
        self.assertIn("documentation_files", contract.writable_scope)
        self.assertNotIn("assigned_backend_scope", contract.writable_scope)
        self.assertEqual(resolve_role("documentation-engineer"), "docs")
        profile = self.agent.ensure_profile()
        self.assertEqual(profile.role, "docs")
        self.assertEqual(profile.department.value, "DOCUMENTATION")

    def test_update_separates_verified_implementation_from_planned_work(self) -> None:
        task = self._task()
        update = self.agent.update_documentation(
            task.id,
            documentation_files=("README.md", "docs/architecture.md"),
            summary="Document the health endpoint and current architecture",
            source_files=("services/orchestrator/app/main.py",),
            implemented_facts=("GET /health is available",),
            planned_facts=("Dashboard metrics remain planned",),
            evidence=(DocumentationEvidence("services/orchestrator/app/main.py", source_symbol="health"),),
            verification=("pytest:tests/test_health.py",),
        )
        self.assertEqual(update.status, "updated")
        self.assertEqual(update.implemented_facts, ("GET /health is available",))
        self.assertEqual(update.planned_facts, ("Dashboard metrics remain planned",))
        self.assertEqual(update.files, ("README.md", "docs/architecture.md"))
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn("documentation_update", {row["topic"] for row in messages})
        self.assertIn(MessageType.RESULT.value, {row["message_type"] for row in messages})

    def test_drift_detection_persists_blocker_evidence(self) -> None:
        task = self._task("Detect documentation drift")
        report = self.agent.detect_drift(
            task.id,
            documented={"api_version": "v1"},
            actual={"api_version": "v2"},
            documentation_files=("docs/api.md",),
            source_files=("services/api.py",),
            evidence=(DocumentationEvidence("services/api.py", test="pytest:tests/test_api.py"),),
        )
        self.assertEqual(report.status, "drift_detected")
        self.assertEqual(report.items[0].documented, "v1")
        self.assertEqual(report.items[0].actual, "v2")
        messages = store.list_messages(project_id=self.project["id"], task_id=task.id, database_path=self.path)
        self.assertIn(MessageType.BLOCKER.value, {row["message_type"] for row in messages})

    def test_source_write_and_unverified_claims_are_rejected(self) -> None:
        task = self._task("Enforce documentation scope")
        with self.assertRaises(ValueError):
            self.agent.update_documentation(
                task.id,
                documentation_files=("services/api.py",),
                summary="Invalid source edit",
                source_files=("services/api.py",),
            )
        with self.assertRaises(ValueError):
            self.agent.update_documentation(
                task.id,
                documentation_files=("docs/api.md",),
                summary="Unsupported implementation claim",
                source_files=(),
                implemented_facts=("The endpoint exists",),
            )

    def test_release_notes_require_verification_for_verified_changes(self) -> None:
        task = self._task("Prepare release notes")
        notes = self.agent.create_release_notes(
            task.id,
            version="2026.09.19",
            entries=("Documentation synchronization workflow added",),
            verified_changes=("Documentation Engineer role contract and drift detection are available",),
            known_limitations=("External markdown rendering is not part of the agent",),
            source_files=("services/orchestrator/app/organization/documentation.py",),
            verification=("python -m unittest tests.test_documentation_agent",),
        )
        self.assertEqual(notes.status, "verified")
        self.assertEqual(notes.version, "2026.09.19")
        self.assertTrue(notes.message_id)


if __name__ == "__main__":
    unittest.main()
