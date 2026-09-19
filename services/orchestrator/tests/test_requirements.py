from __future__ import annotations

import os
import tempfile
import unittest

from app import db
from app.coordination import store as coordination_store
from app.coordination.models import MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.organization.requirements import RequirementsAgent
from app.organization.sales import SalesAgent


class RequirementsAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        db.initialize_database(self.path)
        self.agent = RequirementsAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def test_ambiguous_requirements_are_challenged(self) -> None:
        specification = self.agent.analyze(
            title="Customer portal",
            client_request="Build an application.",
        )
        self.assertEqual(specification.status, "needs_clarification")
        questions = " ".join(specification.open_questions.questions).casefold()
        self.assertIn("target users", questions)
        self.assertIn("concrete behaviors", questions)

    def test_missing_requirements_are_explicit(self) -> None:
        specification = self.agent.analyze(title="Unspecified project", client_request="")
        self.assertFalse(specification.functional_requirements.items)
        self.assertTrue(specification.open_questions.questions)
        self.assertTrue(any("problem" in question.casefold() for question in specification.open_questions.questions))
        self.assertTrue(any(item.classification == "FACT" for item in specification.out_of_scope_items.items))

    def test_conflicting_requirements_are_detected(self) -> None:
        specification = self.agent.analyze(
            title="Client platform",
            client_request=(
                "Build a mobile-only application for browser users with no authentication but login, "
                "using SQLite and PostgreSQL."
            ),
        )
        self.assertEqual(specification.status, "needs_clarification")
        self.assertGreaterEqual(len(specification.risks.items), 2)
        self.assertTrue(any("database" in risk.casefold() for risk in specification.risks.items))
        self.assertTrue(any("authentication" in question.casefold() for question in specification.open_questions.questions))

    def test_acceptance_criteria_are_generated_from_requirements(self) -> None:
        specification = self.agent.analyze(
            title="Inventory service",
            client_request="Build a secure FastAPI API and a React web client for users.",
            deliverables=("API endpoint", "React client", "automated tests"),
            technical_areas=("backend", "frontend", "security", "testing"),
        )
        self.assertGreaterEqual(len(specification.functional_requirements.items), 3)
        self.assertEqual(len(specification.acceptance_criteria.items), 4)
        self.assertEqual(specification.acceptance_criteria.items[0].criterion_id, "AC-001")
        self.assertTrue(all(item.statement.startswith("Given the agreed project scope") for item in specification.acceptance_criteria.items))
        self.assertTrue(all(item.source_classification in {"CLIENT_REQUEST", "RECOMMENDATION"} for item in specification.acceptance_criteria.items))

    def test_handoff_persists_specification_for_project_management(self) -> None:
        sales = SalesAgent(self.path)
        brief = sales.receive(
            source="inbox",
            title="Orders API",
            body="Build a FastAPI API with tests and documentation for users.",
            requirements=("API endpoint", "automated tests", "documentation"),
        )
        specification = self.agent.analyze(brief)
        result = self.agent.handoff(specification, target_role="project_manager")
        self.assertEqual(result["handoff"]["sender_role"], "requirements")
        self.assertEqual(result["handoff"]["recipient_role"], "project_manager")
        self.assertEqual(result["message"]["message_type"], MessageType.HANDOFF.value)
        self.assertIn("RequirementsSpecification", result["handoff"]["artifacts"])
        self.assertEqual(len(coordination_store.list_handoffs(database_path=self.path)), 1)
        self.assertEqual(len(coordination_store.list_messages(database_path=self.path)), 1)
        profile = self.agent.ensure_profile()
        self.assertEqual(profile.role, "requirements")
        self.assertEqual(profile.write_permission, WritePermission.READ_ONLY.value)

    def test_requirements_role_contract_is_read_only_and_routes_to_management(self) -> None:
        contract = get_role_contract("requirements")
        self.assertEqual(contract.id, "requirements")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertEqual(contract.writable_scope, ("none",))
        self.assertEqual(contract.handoff_targets, ("project_manager", "architect", "engineering_manager"))
        self.assertIn("AcceptanceCriteria", contract.output_contract)
        self.assertIn("conflict_detection", contract.capabilities)
        self.assertTrue(set(contract.allowed_tools).isdisjoint({"write_file", "replace_text"}))


if __name__ == "__main__":
    unittest.main()