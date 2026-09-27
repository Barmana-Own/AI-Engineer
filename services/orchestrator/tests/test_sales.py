from __future__ import annotations

import os
import tempfile
import unittest

from app import db
from app.coordination import store as coordination_store
from app.coordination.models import MessageType, WritePermission
from app.organization.sales import ClientMessage, SalesAgent
from app.organization.store import get_employee


class SalesAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        db.initialize_database(self.path)
        self.sales = SalesAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def test_opportunity_qualification_and_clarification_generation(self) -> None:
        brief = self.sales.qualify(
            ClientMessage("inbox", "client-1", "Need a FastAPI API and React client with tests", "2026-09-18T00:00:00Z"),
            title="Inventory service",
            requirements=("API endpoint", "React client"),
        )
        self.assertEqual(brief.qualification, "qualified")
        self.assertEqual(brief.project_type, "software_service")
        self.assertIn("backend", brief.client_needs.technical_areas)
        self.assertIn("frontend", brief.client_needs.technical_areas)
        self.assertTrue(brief.open_questions.questions)
        self.assertIn("acceptance criteria", " ".join(brief.open_questions.questions).casefold())

    def test_profile_persistence_and_proper_handoff(self) -> None:
        brief = self.sales.receive(
            source="inbox",
            title="API project",
            body="Build a small API with tests and documentation.",
            requirements=("API endpoint", "tests", "documentation"),
        )
        profile = get_employee("employee-sales", database_path=self.path)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.role, "sales")
        self.assertEqual(profile.write_permission, WritePermission.READ_ONLY.value)
        handoff = self.sales.handoff(brief)
        self.assertEqual(handoff["handoff"]["sender_role"], "sales")
        self.assertEqual(handoff["handoff"]["recipient_role"], "requirements")
        self.assertEqual(handoff["message"]["message_type"], MessageType.HANDOFF.value)
        persisted = coordination_store.list_handoffs(database_path=self.path)
        self.assertEqual(len(persisted), 1)

    def test_commercial_escalation_requires_owner_and_makes_no_commitment(self) -> None:
        brief = self.sales.receive(source="inbox", title="Enterprise delivery", body="Need a production integration.", requirements=("integration",))
        escalation = self.sales.escalate_commercial(
            brief,
            commitment_type="financial_commitment",
            reason="Client requested a fixed-price quote.",
        )
        self.assertTrue(escalation.requires_human_owner)
        self.assertFalse(escalation.commitment_made)
        self.assertEqual(escalation.recipient_role, "company_director")
        self.assertEqual(escalation.escalation_target, "human_owner")
        messages = coordination_store.list_messages(database_path=self.path)
        self.assertEqual(messages[-1]["message_type"], MessageType.BLOCKER.value)
        self.assertEqual(messages[-1]["recipient_role"], "company_director")
        with self.assertRaises(PermissionError):
            self.sales.make_commitment(brief, amount=1000)

    def test_proposal_is_non_binding_and_rejects_unsupported_commitment_type(self) -> None:
        brief = self.sales.receive(source="inbox", title="Client app", body="Build a web app", requirements=("web app",))
        proposal = self.sales.draft_proposal(brief)
        self.assertTrue(proposal.requires_human_owner_approval)
        self.assertFalse(proposal.financial_commitment_allowed)
        self.assertFalse(proposal.deadline_commitment_allowed)
        self.assertIn("No fixed price", " ".join(proposal.exclusions))
        with self.assertRaises(ValueError):
            self.sales.escalate_commercial(brief, commitment_type="unsupported", reason="x")


if __name__ == "__main__":
    unittest.main()
