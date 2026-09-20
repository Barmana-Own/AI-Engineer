from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app import db
from app.coordination.supervisor import Supervisor
from app.organization.director import TeamPlanner
from app.organization.store import get_project_team_plan


class DynamicExecutionTeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "dynamic-team.db"
        db.initialize_database(self.database_path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _project(self, name: str) -> str:
        return str(
            db.create_project(
                name,
                name.casefold().replace(" ", "-"),
                database_path=self.database_path,
            )["id"]
        )

    def _start(self, objective: str) -> dict[str, object]:
        return Supervisor(self.database_path).start_objective(
            project_id=self._project(objective[:24]),
            objective=objective,
        )

    @staticmethod
    def _roles(started: dict[str, object]) -> set[str]:
        return {str(task["role"]) for task in started["tasks"]}

    def test_backend_only_project_does_not_schedule_frontend(self) -> None:
        started = self._start("Fix the backend API endpoint and add regression tests")
        roles = self._roles(started)
        self.assertIn("backend", roles)
        self.assertNotIn("frontend", roles)
        self.assertEqual(
            roles,
            {"engineering_manager", "backend", "tester", "reviewer", "release_verifier"},
        )

    def test_frontend_only_project_does_not_schedule_backend(self) -> None:
        started = self._start("Fix the frontend UI component and add client tests")
        roles = self._roles(started)
        self.assertIn("frontend", roles)
        self.assertNotIn("backend", roles)
        self.assertEqual(
            roles,
            {"engineering_manager", "frontend", "tester", "reviewer", "release_verifier"},
        )

    def test_full_stack_project_schedules_only_required_cross_component_roles(self) -> None:
        started = self._start(
            "Build a full-stack web application with a backend API, "
            "frontend React client, integration tests and documentation"
        )
        roles = self._roles(started)
        self.assertTrue(
            {
                "project_manager",
                "requirements",
                "engineering_manager",
                "architect",
                "backend",
                "frontend",
                "integration",
                "docs",
                "tester",
                "reviewer",
                "release_verifier",
            }
            <= roles
        )
        self.assertNotIn("seo_manager", roles)

    def test_small_bug_fix_uses_minimal_general_team(self) -> None:
        started = self._start("Fix an isolated parser typo")
        roles = self._roles(started)
        self.assertEqual(
            roles,
            {"engineering_manager", "implementer", "tester", "reviewer", "release_verifier"},
        )
        self.assertNotIn("architect", roles)
        self.assertNotIn("frontend", roles)
        self.assertNotIn("backend", roles)

    def test_security_sensitive_work_adds_security_review(self) -> None:
        started = self._start("Fix authentication and authorization on the API endpoint")
        roles = self._roles(started)
        self.assertIn("security", roles)
        self.assertIn("backend", roles)
        self.assertNotIn("frontend", roles)

    def test_documentation_only_work_avoids_engineering_implementers(self) -> None:
        started = self._start("Update the README and user guide")
        roles = self._roles(started)
        self.assertEqual(
            roles,
            {"engineering_manager", "docs", "reviewer", "release_verifier"},
        )
        self.assertNotIn("backend", roles)
        self.assertNotIn("frontend", roles)

    def test_seo_project_uses_seo_manager_and_specialist_flow(self) -> None:
        started = self._start(
            "Run an SEO audit with keyword mapping, canonical and sitemap verification"
        )
        roles = self._roles(started)
        self.assertIn("seo_manager", roles)
        self.assertIn("seo_specialist", roles)
        self.assertNotIn("backend", roles)
        self.assertNotIn("frontend", roles)

    def test_plan_and_assignments_survive_restart_without_regeneration(self) -> None:
        project_id = self._project("restart-plan")
        first = Supervisor(self.database_path).start_objective(
            project_id=project_id,
            objective="Fix the backend API endpoint and add regression tests",
        )
        second = Supervisor(self.database_path).start_objective(
            project_id=project_id,
            objective="Fix the backend API endpoint and add regression tests",
            run_id=str(first["run_id"]),
        )
        self.assertTrue(second["resumed"])
        self.assertEqual(
            [task["id"] for task in first["tasks"]],
            [task["id"] for task in second["tasks"]],
        )
        persisted = get_project_team_plan(project_id, database_path=self.database_path)
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted["selected_roles"], ["engineering_manager", "backend", "tester", "reviewer", "release_verifier"])
        self.assertEqual(set(persisted["assigned_tasks"]), set(persisted["selected_roles"]))
        self.assertTrue(all(persisted["assigned_tasks"][role] for role in persisted["selected_roles"]))

    def test_task_graph_contains_only_roles_in_authoritative_plan(self) -> None:
        started = self._start("Fix the frontend UI component")
        plan_roles = set(started["team_plan"]["selected_roles"])
        task_roles = self._roles(started)
        self.assertEqual(task_roles, plan_roles)
        self.assertFalse({"backend", "seo_manager", "security"} & task_roles)


if __name__ == "__main__":
    unittest.main()
