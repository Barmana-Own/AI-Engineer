from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import db
from app.coordination.supervisor import Supervisor
from app.organization.director import TeamPlanner
from app.organization.intake import OpportunityIntakeService
from app.organization.seo_manager import SEOManagerAgent
from app.organization.seo_specialist import SEOSpecialistAgent


class SalesSeoWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "sales-seo.db"
        db.initialize_database(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sales_qualification_persists_structured_state_and_handoff(self) -> None:
        intake = OpportunityIntakeService(self.path)
        result = intake.receive(
            source="client",
            title="Inventory API",
            body="Build a FastAPI API with tests and documentation.",
            requirements=("API endpoint", "tests", "documentation"),
        )
        opportunity = result["opportunity"]
        self.assertEqual(opportunity["status"], "QUALIFIED")
        self.assertEqual(opportunity["brief"]["title"], "Inventory API")
        self.assertEqual(result["handoff"]["handoff"]["recipient_role"], "requirements")
        self.assertFalse(result["proposal"]["financial_commitment_allowed"])

    def test_sales_owner_gate_blocks_unsupported_fit_until_approval(self) -> None:
        intake = OpportunityIntakeService(self.path)
        result = intake.receive(
            source="client",
            title="Specialized project",
            body="Build a backend API integration.",
            requirements=("backend API",),
            company_capabilities=("frontend",),
        )
        self.assertEqual(result["opportunity"]["status"], "WAITING_OWNER")
        with self.assertRaises(PermissionError):
            intake.convert(result["opportunity"]["opportunity_id"], workspace=str(self.temp.name))

    def test_conversion_uses_requirements_director_and_existing_supervisor(self) -> None:
        intake = OpportunityIntakeService(self.path)
        incoming = intake.receive(
            source="client",
            title="SEO API service",
            body="Build a FastAPI API for SEO audit results with tests.",
            requirements=("API endpoint", "tests"),
        )
        converted = intake.convert(
            incoming["opportunity"]["opportunity_id"],
            workspace=str(self.temp.name),
            owner_approved=True,
        )
        self.assertEqual(converted["opportunity"]["status"], "CONVERTED_TO_PROJECT")
        started = intake.start(incoming["opportunity"]["opportunity_id"])["execution"]
        task_roles = {str(task["role"]) for task in started["tasks"]}
        plan_roles = set(started["team_plan"]["selected_roles"])
        self.assertEqual(task_roles, plan_roles)
        self.assertIn("requirements", task_roles)
        self.assertIn("engineering_manager", task_roles)

    def test_conversion_is_idempotent_on_isolated_database(self) -> None:
        intake = OpportunityIntakeService(self.path)
        incoming = intake.receive(
            source="client",
            title="Idempotent SEO project",
            body="Build and implement technical SEO improvements for an existing website, with verification.",
            requirements=("technical SEO audit", "implementation", "verification"),
        )
        opportunity_id = incoming["opportunity"]["opportunity_id"]
        first = intake.convert(
            opportunity_id,
            workspace=str(self.temp.name),
            owner_approved=True,
        )
        second = intake.convert(
            opportunity_id,
            workspace=str(self.temp.name),
            owner_approved=True,
        )
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["project"]["id"], first["project"]["id"])

    def test_keyword_only_seo_uses_minimal_seo_team(self) -> None:
        roles = {role for role, _ in TeamPlanner().select_roles("Keyword research and search intent mapping only")}
        self.assertIn("seo_manager", roles)
        self.assertIn("seo_specialist", roles)
        self.assertIn("researcher", roles)
        self.assertNotIn("backend", roles)
        self.assertNotIn("frontend", roles)
        self.assertNotIn("devops", roles)

    def test_technical_seo_improvement_expands_only_required_engineers(self) -> None:
        roles = {role for role, _ in TeamPlanner().select_roles("Audit and improve technical SEO: fix canonical tags and redirect chains")}
        self.assertIn("seo_manager", roles)
        self.assertIn("seo_specialist", roles)
        self.assertIn("frontend", roles)
        self.assertIn("devops", roles)
        self.assertIn("integration", roles)
        self.assertNotIn("backend", roles)

    def test_seo_finding_creates_engineering_task_and_verification_revision(self) -> None:
        project = db.create_project("SEO site", str(self.temp.name), database_path=self.path)
        project_id = str(project["id"])
        started = Supervisor(self.path).start_objective(
            project_id=project_id,
            objective="Audit and improve technical SEO: fix canonical tags",
        )
        manager_task = next(task for task in started["tasks"] if task["role"] == "seo_manager")
        manager = SEOManagerAgent(self.path)
        backlog = manager.delegate_task(
            manager_task["id"],
            title="Fix canonical tag",
            problem="Canonical is missing",
            responsible_role="frontend",
            evidence=("HTML inspection found no canonical",),
            acceptance_criteria=("Canonical resolves to the preferred URL",),
            verification_method="Inspect rendered HTML",
            priority="HIGH",
            affected_scope=("/products",),
        )
        specialist = SEOSpecialistAgent(self.path)
        failed = specialist.verify_implementation(
            backlog.task_id,
            observed={"canonical": "/wrong"},
            expected={"canonical": "/products"},
            evidence=({"description": "HTML still points to /wrong"},),
            verification_method="HTML inspection",
            responsible_role="frontend",
        )
        self.assertEqual(failed.status, "SEO_FAILED")
        passed = specialist.verify_implementation(
            backlog.task_id,
            observed={"canonical": "/products"},
            expected={"canonical": "/products"},
            evidence=({"description": "Rendered HTML points to /products"},),
            verification_method="HTML inspection",
            responsible_role="frontend",
        )
        self.assertEqual(passed.status, "SEO_VERIFIED")

    def test_seo_projects_keep_site_context_isolated(self) -> None:
        first = TeamPlanner().select_roles("Audit SEO for site alpha")
        second = TeamPlanner().select_roles("Keyword research for site beta")
        self.assertEqual(
            {role for role, _ in first} & {"seo_manager", "seo_specialist"},
            {"seo_manager", "seo_specialist"},
        )
        self.assertEqual(
            {role for role, _ in second} & {"seo_manager", "seo_specialist"},
            {"seo_manager", "seo_specialist"},
        )
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()

