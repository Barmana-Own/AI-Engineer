from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import db
from app.coordination.roles import get_role_contract
from app.organization.director import CompanyDirector, TeamPlanner
from app.organization.models import Department, EmployeeStatus
from app.organization.store import (
    ensure_employee,
    get_employee,
    get_project_organization,
    list_employees,
    update_employee_status,
)


class OrganizationCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "organization.db"
        db.initialize_database(self.database_path)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def _project(self, name: str = "Project") -> dict[str, object]:
        return db.create_project(
            name,
            name.casefold().replace(" ", "-"),
            database_path=self.database_path,
        )

    def test_persistent_employee_profile_and_restart_recovery(self) -> None:
        first = ensure_employee(
            "company_director",
            database_path=self.database_path,
        )
        second = ensure_employee(
            "director",
            database_path=self.database_path,
        )
        self.assertEqual(first.agent_id, "employee-company-director")
        self.assertEqual(first.agent_id, second.agent_id)
        self.assertEqual(first.department, Department.EXECUTIVE)
        self.assertEqual(first.status, EmployeeStatus.AVAILABLE)

        updated = update_employee_status(
            first.agent_id,
            "planning",
            current_tasks=["org-review"],
            database_path=self.database_path,
        )
        self.assertEqual(updated.status, EmployeeStatus.PLANNING)
        reopened = get_employee(first.agent_id, database_path=self.database_path)
        self.assertIsNotNone(reopened)
        assert reopened is not None
        self.assertEqual(reopened.current_tasks, ("org-review",))
        self.assertEqual(reopened.status, EmployeeStatus.PLANNING)

    def test_department_assignment_and_role_contract_compatibility(self) -> None:
        roles = (
            "company_director", "project_manager", "engineering_manager",
            "requirements", "architect", "researcher", "backend", "frontend",
            "implementer", "integration", "tester", "debugger", "reviewer",
            "security", "docs", "release_verifier", "operations",
        )
        for role in roles:
            profile = ensure_employee(role, database_path=self.database_path)
            contract = get_role_contract(role)
            self.assertEqual(profile.role, contract.id)
            self.assertTrue(profile.department.value)
            self.assertIn(profile.write_permission, {"read_only", "scoped_write", "workspace_write"})
        self.assertEqual(
            get_role_contract("company-director").id,
            "company_director",
        )
        self.assertEqual(
            get_role_contract("engineering-manager").id,
            "engineering_manager",
        )

    def test_company_director_creates_small_team_and_persists_project_org(self) -> None:
        project = self._project("Small Project")
        plan, organization = CompanyDirector().organize_project(
            str(project["id"]),
            "Add one endpoint and tests",
            complexity="small",
            priority=70,
            database_path=self.database_path,
        )
        self.assertEqual(plan.complexity.value, "small")
        self.assertEqual(
            {member.role for member in organization.members},
            {"engineering_manager", "backend", "tester", "reviewer", "release_verifier"},
        )
        self.assertEqual(organization.project["priority"], 70)
        self.assertEqual(
            organization.project["engineering_manager_id"],
            "employee-engineering-manager",
        )
        self.assertIsNone(organization.project["project_manager_id"])
        self.assertEqual(organization.project["team_state"], "forming")
        with db.connect(self.database_path) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM project_team_members WHERE project_id = ?",
                (project["id"],),
            ).fetchone()[0]
        self.assertEqual(count, 5)
        report = CompanyDirector().executive_report(
            str(project["id"]), database_path=self.database_path
        )
        self.assertEqual(report["team_size"], 5)
        self.assertTrue(report["delegates_technical_execution"])

    def test_large_team_uses_declared_complexity_and_required_departments(self) -> None:
        project = self._project("Large Project")
        plan, organization = CompanyDirector().organize_project(
            str(project["id"]),
            "A production platform with backend, frontend, security, and integration",
            complexity="large",
            technologies=["Python", "React", "SQLite", "CI"],
            risks=["security"],
            deliverables=["api", "client", "tests", "docs"],
            database_path=self.database_path,
        )
        expected = {
            "project_manager", "requirements", "engineering_manager", "architect",
            "backend", "frontend", "integration", "tester", "reviewer", "security", "docs",
            "release_verifier",
        }
        self.assertEqual({member.role for member in organization.members}, expected)
        self.assertEqual(plan.project_manager_id, "employee-project-manager")
        self.assertIn(Department.SECURITY, plan.departments)
        self.assertIn(Department.OPERATIONS, plan.departments)
        self.assertEqual(len(list_employees(database_path=self.database_path)), 13)

    def test_complexity_inference_is_deterministic_and_bounded(self) -> None:
        planner = TeamPlanner()
        self.assertEqual(
            planner.infer_complexity("tiny change").value,
            "small",
        )
        self.assertEqual(
            planner.infer_complexity(
                "production backend integration",
                technologies=["Python"],
            ).value,
            "large",
        )
        with self.assertRaises(ValueError):
            planner.plan("p", "valid objective", complexity="unknown")

    def test_organization_migration_is_idempotent(self) -> None:
        db.initialize_database(self.database_path)
        db.initialize_database(self.database_path)
        with db.connect(self.database_path) as connection:
            version = connection.execute(
                "SELECT version FROM schema_version WHERE id = 1"
            ).fetchone()[0]
            self.assertEqual(version, db.SCHEMA_VERSION)
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertTrue({"agent_profiles", "project_team_members"} <= tables)


if __name__ == "__main__":
    unittest.main()
