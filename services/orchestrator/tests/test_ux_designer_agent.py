from __future__ import annotations

import os
import tempfile
import unittest

from app.coordination import store
from app.coordination.models import MessageType, WritePermission
from app.coordination.roles import get_role_contract
from app.db import create_project, initialize_database
from app.organization import (
    AccessibilityRequirement,
    ComponentRequirement,
    DesignNotes,
    InteractionSpecification,
    ResponsiveRule,
    ScreenDefinition,
    UXDesignerAgent,
    UserFlow,
)


class UXDesignerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("UX project", "Experience design validation", database_path=self.path)
        self.designer = UXDesignerAgent(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _design(self):
        return self.designer.design(
            self.project["id"],
            "Authenticated project workflow",
            objective="Let a project owner review work and recover from validation errors.",
            user_flows=(
                UserFlow(
                    "flow-review",
                    "Review a project",
                    "Understand current delivery status",
                    actors=("project_owner",),
                    steps=("open dashboard", "inspect status", "open task details"),
                    entry_point="Project dashboard",
                    success_state="Status and next action are clear",
                    alternate_states=("loading", "empty", "permission denied"),
                    requirement_ids=("FR-001",),
                ),
            ),
            screens=(
                ScreenDefinition(
                    "screen-dashboard",
                    "Project dashboard",
                    "Show progress and blockers",
                    audience=("project_owner",),
                    hierarchy=("project title", "phase", "blockers", "next action"),
                    primary_actions=("open task", "retry request"),
                    states=("loading", "empty", "error", "success"),
                    responsive_notes=("stack summary cards on mobile",),
                    requirement_ids=("FR-001", "NFR-ACCESS"),
                ),
            ),
            interactions=(
                InteractionSpecification(
                    "retry request",
                    "Retry the failed request without duplicate submission.",
                    triggers=("activate retry",),
                    feedback=("show pending state", "announce completion"),
                    error_handling=("retain error and offer another retry",),
                    keyboard_behavior=("button is reachable by Tab",),
                ),
            ),
            components=(
                ComponentRequirement(
                    "StatusBanner",
                    "Communicate phase and blockers.",
                    variants=("success", "warning", "error"),
                    states=("loading", "dismissed"),
                    data_requirements=("phase", "message"),
                    accessibility=("use role=status",),
                    responsive_behavior=("wrap content on narrow screens",),
                ),
            ),
            accessibility_requirements=(
                AccessibilityRequirement(
                    "NFR-ACCESS",
                    "dashboard",
                    "WCAG keyboard access",
                    "All actions are operable without a pointer.",
                    "Keyboard walkthrough",
                ),
            ),
            responsive_rules=(
                ResponsiveRule(
                    "dashboard summary",
                    mobile="single column",
                    tablet="two columns",
                    desktop="four columns",
                    overflow="stack rather than clip",
                    priority="high",
                ),
            ),
            design_notes=DesignNotes(
                principles=("status is visible", "errors are recoverable"),
                assumptions=("project owners have authenticated access",),
                risks=("dense task data may overwhelm mobile users",),
                evidence=("requirements:FR-001",),
            ),
            requirement_ids=("FR-001", "NFR-ACCESS"),
            requirement_traceability=(
                {"requirement_id": "FR-001", "flows": ["flow-review"], "screens": ["screen-dashboard"]},
                {"requirement_id": "NFR-ACCESS", "flows": [], "screens": ["screen-dashboard"]},
            ),
        )

    def test_design_role_contract_and_profile_are_read_only(self) -> None:
        contract = get_role_contract("ux_designer")
        self.assertEqual(contract.write_permission, WritePermission.READ_ONLY)
        self.assertIn("user_flows", contract.capabilities)
        self.assertIn("accessibility_requirements", contract.capabilities)
        self.assertEqual(contract.handoff_targets, ("frontend",))
        profile = self.designer.ensure_profile()
        self.assertEqual(profile.role, "ux_designer")
        self.assertEqual(profile.write_permission, WritePermission.READ_ONLY.value)

    def test_screen_specification_and_interactions_are_persisted(self) -> None:
        design = self._design()
        stored = self.designer.get_design(design.design_id)
        self.assertEqual(stored.screens[0]["name"], "Project dashboard")
        self.assertEqual(stored.interactions[0]["target"], "retry request")
        self.assertEqual(stored.components[0]["name"], "StatusBanner")
        messages = store.list_messages(project_id=self.project["id"], topic="ux_design_specification", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.PROPOSAL.value)

    def test_accessibility_and_responsive_requirements_are_structured(self) -> None:
        design = self._design()
        self.assertEqual(design.accessibility_requirements[0]["requirement_id"], "NFR-ACCESS")
        self.assertEqual(design.responsive_rules[0]["priority"], "high")
        self.assertIn("WCAG keyboard access", design.accessibility_requirements[0]["guideline"])

    def test_requirement_to_design_traceability_is_persisted(self) -> None:
        design = self._design()
        trace = {row["requirement_id"]: row for row in design.design_notes.requirement_traceability}
        self.assertEqual(trace["FR-001"]["screens"], ["screen-dashboard"])
        self.assertEqual(trace["NFR-ACCESS"]["screens"], ["screen-dashboard"])
        stored = self.designer.get_design(design.design_id)
        self.assertEqual(stored.requirement_ids, ("FR-001", "NFR-ACCESS"))

    def test_design_handoff_targets_frontend_and_persists_artifacts(self) -> None:
        design = self._design()
        result = self.designer.handoff(
            design,
            target_role="frontend",
            remaining_work=("Implement the dashboard without changing the API contract.",),
            verification=("Frontend review required",),
        )
        self.assertEqual(result["handoff"]["recipient_role"], "frontend")
        self.assertIn("UserFlows", result["handoff"]["artifacts"])
        self.assertIn("AccessibilityRequirements", result["handoff"]["artifacts"])
        messages = store.list_messages(project_id=self.project["id"], topic="ux_design_handoff", database_path=self.path)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message_type"], MessageType.HANDOFF.value)


if __name__ == "__main__":
    unittest.main()
