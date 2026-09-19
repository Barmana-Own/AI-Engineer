from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.collaboration_store import list_decisions
from app.coordination.models import MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import SoftwareArchitectAgent


class SoftwareArchitectAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Architect project", "Architecture validation", database_path=self.path)
        self.architect = SoftwareArchitectAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _proposal(self):
        return self.architect.propose(
            self.project["id"],
            "Layered service architecture",
            context="Evolve the existing modular service without merging boundaries.",
            components=(
                {"name": "orchestrator", "responsibility": "coordination"},
                {"name": "model-gateway", "responsibility": "provider routing"},
            ),
            boundaries=(
                {"from": "orchestrator", "to": "model-gateway", "contract": "model request"},
            ),
            interfaces=(
                {"name": "ModelGateway", "direction": "outbound"},
            ),
            api_contracts=(
                {"name": "health", "method": "GET", "path": "/health", "response": "status"},
            ),
            data_flow=(
                {"source": "orchestrator", "destination": "model-gateway", "data": "prompt"},
            ),
            technology_decisions=(
                {"area": "persistence", "choice": "SQLite", "rationale": "preserve existing deployment"},
            ),
            architecture_risks=(
                {"title": "provider outage", "impact": "run delay", "mitigation": "fallback routing"},
            ),
            alternatives=(
                {"choice": "merge services", "reason_rejected": "loses operational boundaries"},
            ),
            tradeoffs=("Retain modular boundaries while adding explicit contracts.",),
            evidence=("inspection:orchestrator",),
        )

    def test_role_contract_and_profile_are_read_only_and_challengeable(self) -> None:
        contract = get_role_contract("architect")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("architecture_proposal", contract.capabilities)
        self.assertIn("architecture_challenges", contract.capabilities)
        self.assertIn("security", contract.handoff_targets)
        profile = self.architect.ensure_profile()
        self.assertEqual(profile.role, "architect")
        self.assertEqual(profile.write_permission, WritePermission.READ_ONLY.value)

    def test_architecture_proposal_and_component_contract_persist(self) -> None:
        proposal = self._proposal()
        self.assertEqual(proposal.project_id, self.project["id"])
        self.assertEqual(proposal.component_map.components[0]["name"], "orchestrator")
        stored = self.architect.get_proposal(proposal.proposal_id)
        self.assertEqual(stored.proposal_id, proposal.proposal_id)
        messages = store.list_messages(project_id=self.project["id"], topic="architecture_proposal", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.PROPOSAL.value)

    def test_decision_record_links_proposal_and_evidence(self) -> None:
        proposal = self._proposal()
        result = self.architect.record_decision(
            proposal,
            "Keep the existing service boundary and formalize the gateway contract.",
            decision_maker="engineering_manager",
            options=("merge services", "preserve boundaries"),
            arguments=("lower regression risk",),
            evidence=("review:boundary-analysis",),
        )
        decisions = list_decisions(project_id=self.project["id"], database_path=self.path)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision_maker"], "engineering_manager")
        self.assertEqual(result["decision"]["decision_id"], decisions[0]["decision_id"])
        self.assertEqual(store.list_messages(project_id=self.project["id"], topic="architecture_decision", database_path=self.path)[0]["message_type"], MessageType.DECISION.value)

    def test_challenge_and_evidence_based_revision_persist(self) -> None:
        proposal = self._proposal()
        challenge = self.architect.challenge(
            proposal,
            "security",
            "Gateway trust boundary",
            "The proposal must document token validation and prevent provider credentials from crossing the boundary.",
            evidence=("security:threat-model",),
            requested_changes=("add credential boundary",),
        )
        self.assertEqual(challenge.challenger_role, "security")
        revision = self.architect.revise(
            proposal,
            reason="Security challenge requires an explicit credential boundary.",
            changed_areas=("trust boundary", "security controls"),
            evidence=(f"challenge:{challenge.challenge_id}",),
        )
        self.assertEqual(revision.proposal.version, 2)
        self.assertEqual(revision.proposal.revision_of, proposal.proposal_id)
        messages = store.list_messages(project_id=self.project["id"], database_path=self.path)
        self.assertEqual(len([row for row in messages if row["message_type"] == MessageType.CHALLENGE.value]), 1)
        self.assertEqual(len([row for row in messages if row["message_type"] == MessageType.PROPOSAL.value]), 2)

    def test_handoff_to_engineer_persists_artifacts_and_message(self) -> None:
        proposal = self._proposal()
        result = self.architect.handoff(
            proposal,
            target_role="backend",
            decision_ids=("decision-placeholder",),
            remaining_work=("Implement the documented gateway contract.",),
            verification=("contract review required",),
        )
        self.assertEqual(result["handoff"]["recipient_role"], "backend")
        self.assertIn("ComponentMap", result["handoff"]["artifacts"])
        messages = store.list_messages(project_id=self.project["id"], topic="architecture_handoff", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.HANDOFF.value)


if __name__ == "__main__":
    unittest.main()
