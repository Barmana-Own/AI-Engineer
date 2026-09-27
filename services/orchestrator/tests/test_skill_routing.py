from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.skill_registry import SkillRegistry
from app.skill_routing import (
    SkillContextLoader,
    SkillRouteRequest,
    SkillRouter,
    SkillRoutingError,
    UnknownRoleError,
    build_skill_evidence,
    effective_tool_permissions,
    evaluate_quality_gates,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class SkillRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SkillRegistry(REPOSITORY_ROOT)
        cls.router = SkillRouter(cls.registry)

    def route_ids(self, **kwargs: object) -> set[str]:
        request = SkillRouteRequest(
            task_objective=str(kwargs.pop("task_objective")),
            assigned_role=str(kwargs.pop("assigned_role")),
            **kwargs,
        )
        return set(self.router.route(request).skill_ids)

    def test_backend_database_task_gets_backend_and_database_skills_only(self) -> None:
        selected = self.route_ids(
            task_objective="Implement a SQLite migration for the transaction schema.",
            assigned_role="backend",
            project_type="backend maintenance",
        )
        self.assertIn("backend-architecture", selected)
        self.assertIn("database-architecture", selected)
        self.assertNotIn("design-system-ui-architecture", selected)
        self.assertNotIn("frontend-architecture", selected)

    def test_frontend_task_gets_ui_and_frontend_skills_without_database_pipeline(self) -> None:
        selected = self.route_ids(
            task_objective="Create a React responsive accessibility layout.",
            assigned_role="frontend",
            project_type="frontend",
        )
        self.assertEqual(
            selected,
            {"design-system-ui-architecture", "frontend-architecture"},
        )
        self.assertNotIn("database-architecture", selected)
        self.assertNotIn("backend-architecture", selected)

    def test_security_auth_task_gets_auth_and_application_security(self) -> None:
        selected = self.route_ids(
            task_objective="Review authentication middleware and authorization boundaries.",
            assigned_role="security",
            risk="high",
        )
        self.assertIn("authentication-authorization", selected)
        self.assertIn("application-security", selected)
        self.assertNotIn("frontend-architecture", selected)

    def test_testing_debugging_devops_and_release_roles_are_scoped(self) -> None:
        self.assertEqual(
            self.route_ids(task_objective="Run regression tests.", assigned_role="tester"),
            {"software-testing", "qa-debugging"},
        )
        self.assertEqual(
            self.route_ids(task_objective="Reproduce and fix the failing test.", assigned_role="debugger"),
            {"software-testing", "qa-debugging"},
        )
        self.assertEqual(
            self.route_ids(task_objective="Prepare a production deployment and health check.", assigned_role="devops"),
            {"deployment-production"},
        )
        release = self.route_ids(
            task_objective="Verify the release acceptance criteria.",
            assigned_role="release_verifier",
        )
        self.assertIn("fullstack-final-review", release)
        self.assertNotIn("frontend-architecture", release)

    def test_docs_only_does_not_activate_engineering_pipeline(self) -> None:
        result = self.router.route(
            SkillRouteRequest(
                task_objective="Documentation-only README and release notes update.",
                assigned_role="docs",
                project_type="documentation-only",
            )
        )
        self.assertEqual(result.skill_ids, ())
        self.assertEqual(result.stage_dependencies, ())

        project = self.router.route_project(
            SkillRouteRequest(
                task_objective="Update the README documentation only.",
                assigned_role="project_manager",
                project_type="docs-only",
            )
        )
        self.assertEqual(project.skill_ids, ())

        api_docs = self.router.route_project(
            SkillRouteRequest(
                task_objective="Create API documentation only.",
                assigned_role="project_manager",
                project_type="documentation-only",
            )
        )
        self.assertEqual(api_docs.skill_ids, ())

    def test_backend_only_project_has_contextual_testing_and_review_stages(self) -> None:
        result = self.router.route_project(
            SkillRouteRequest(
                task_objective="Fix a FastAPI backend endpoint and add regression tests.",
                assigned_role="project_manager",
                project_type="backend-only",
            )
        )
        selected = set(result.skill_ids)
        self.assertIn("backend-architecture", selected)
        self.assertIn("software-testing", selected)
        self.assertIn("fullstack-final-review", selected)
        self.assertNotIn("design-system-ui-architecture", selected)
        self.assertNotIn("frontend-architecture", selected)
        final = next(item for item in result.stage_dependencies if item.skill_id == "fullstack-final-review")
        self.assertIn("backend-architecture", final.depends_on)

    def test_full_stack_project_activates_relevant_skills_without_forcing_deployment(self) -> None:
        result = self.router.route_project(
            SkillRouteRequest(
                task_objective="Build a full-stack web application with authentication, API, frontend, tests, and review.",
                assigned_role="project_manager",
                project_type="full-stack",
            )
        )
        selected = set(result.skill_ids)
        expected = {
            "project-analysis-prompt-engineering",
            "design-system-ui-architecture",
            "frontend-architecture",
            "backend-architecture",
            "api-integration",
            "authentication-authorization",
            "application-security",
            "software-testing",
            "qa-debugging",
            "fullstack-final-review",
        }
        self.assertTrue(expected.issubset(selected))
        self.assertNotIn("deployment-production", selected)

    def test_full_stack_documentation_deliverable_does_not_trigger_docs_only_route(self) -> None:
        result = self.router.route_project(
            SkillRouteRequest(
                task_objective="Build a small full-stack application with authentication, API, frontend, tests, and documentation.",
                assigned_role="project_manager",
                project_type="full-stack",
            )
        )
        self.assertIn("frontend-architecture", result.skill_ids)
        self.assertIn("backend-architecture", result.skill_ids)
        self.assertIn("software-testing", result.skill_ids)
        self.assertNotEqual(result.skill_ids, ())
    def test_full_stack_documentation_deliverable_does_not_trigger_docs_only_route(self) -> None:
        result = self.router.route_project(
            SkillRouteRequest(
                task_objective="Build a small full-stack application with authentication, API, frontend, tests, and documentation.",
                assigned_role="project_manager",
                project_type="full-stack",
            )
        )
        self.assertIn("frontend-architecture", result.skill_ids)
        self.assertIn("backend-architecture", result.skill_ids)
        self.assertIn("software-testing", result.skill_ids)
        self.assertNotEqual(result.skill_ids, ())
    def test_project_selected_skills_are_read_only_overview_for_engineering_manager(self) -> None:
        result = self.router.route(
            SkillRouteRequest(
                task_objective="Coordinate the selected project skills.",
                assigned_role="engineering_manager",
                project_skill_ids=("backend-architecture", "software-testing"),
            )
        )
        self.assertEqual(set(result.skill_ids), {"backend-architecture", "software-testing"})
        self.assertTrue(all(not item.required for item in result.selections))

    def test_unknown_role_is_rejected(self) -> None:
        with self.assertRaises(UnknownRoleError):
            self.router.route(SkillRouteRequest("Do work", "unregistered-role"))

    def test_lazy_context_loading_does_not_load_irrelevant_skills(self) -> None:
        result = self.router.route(
            SkillRouteRequest(
                task_objective="Create a responsive React layout.",
                assigned_role="frontend",
                project_type="frontend-only",
            )
        )
        reference = self.registry.get("frontend-architecture").references[0]
        loaded = SkillContextLoader(self.registry).load(
            result,
            task_id="task-1",
            role="frontend",
            project_id="project-1",
            reference_names={"frontend-architecture": (reference,)},
        )
        self.assertEqual({item.skill_id for item in loaded}, set(result.skill_ids))
        frontend = next(item for item in loaded if item.skill_id == "frontend-architecture")
        self.assertEqual(tuple(frontend.references), (reference,))
        self.assertNotIn("backend-architecture", {item.skill_id for item in loaded})

    def test_context_loader_rejects_undeclared_reference(self) -> None:
        result = self.router.route(
            SkillRouteRequest("Implement a backend endpoint", "backend")
        )
        with self.assertRaises(SkillRoutingError):
            SkillContextLoader(self.registry).load(
                result,
                task_id="task-1",
                role="backend",
                project_id="project-1",
                reference_names={"backend-architecture": ("not-declared.md",)},
            )

    def test_context_loader_requires_router_result_and_matching_role(self) -> None:
        result = self.router.route(SkillRouteRequest("Implement a backend endpoint", "backend"))
        loader = SkillContextLoader(self.registry)
        with self.assertRaises(SkillRoutingError):
            loader.load(result.selections, task_id="task-1", role="backend", project_id="project-1")
        with self.assertRaises(SkillRoutingError):
            loader.load(result, task_id="task-1", role="reviewer", project_id="project-1")

    def test_skill_permissions_cannot_expand_role_permissions(self) -> None:
        permissions = effective_tool_permissions(
            role_tools={"read_file", "diff"},
            task_tools={"read_file", "run_terminal", "diff"},
            global_tools={"read_file", "run_terminal", "diff"},
            selected_skill_ids=("fullstack-final-review",),
            registry=self.registry,
        )
        self.assertEqual(permissions, {"read_file", "diff"})

    def test_quality_gates_require_objective_evidence(self) -> None:
        selections = self.router.route(
            SkillRouteRequest("Run tests and review the release", "tester")
        ).selections
        blocked = evaluate_quality_gates(selections, {})
        self.assertTrue(blocked)
        self.assertTrue(all(item.status == "blocked" for item in blocked))

        evidence = {
            "software-testing": {"tests_passed": True, "checks_run": ["pytest -q"]},
            "qa-debugging": {"regressions_absent": True, "checks_run": ["pytest -q"]},
        }
        passed = evaluate_quality_gates(selections, evidence)
        self.assertTrue(all(item.status == "passed" for item in passed))

    def test_structured_skill_evidence_has_required_contract(self) -> None:
        evidence = build_skill_evidence(
            skill_id="software-testing",
            task_id="task-1",
            agent_id="tester-1",
            checks_run=("pytest -q",),
            gate_status="passed",
        )
        self.assertEqual(
            set(evidence),
            {
                "skill_id", "task_id", "agent_id", "artifacts_created", "checks_run",
                "findings", "gate_status", "handoff", "evidence",
            },
        )

    def test_skill_selection_and_trace_persist_on_existing_task(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory) / "orchestrator.db"
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                project = db.create_project("Routing", "routing-test")
                result = self.router.route(
                    SkillRouteRequest(
                        task_objective="Implement a database migration.",
                        assigned_role="backend",
                        project_id=project["id"],
                    )
                )
                task = db.create_task(project["id"], "Implement a database migration.")
                updated = db.set_task_skill_route(
                    task["id"],
                    [selection.as_dict() for selection in result.selections],
                    trace=[result.as_dict()],
                )
                self.assertEqual(
                    set(item["skill_id"] for item in updated["skill_selections"]),
                    set(result.skill_ids),
                )
                self.assertEqual(updated["skill_trace"][0]["role"], "backend")
                evidence = build_skill_evidence(
                    skill_id="database-architecture",
                    task_id=task["id"],
                    agent_id="backend-1",
                    checks_run=("migration test",),
                )
                updated = db.append_task_skill_evidence(task["id"], evidence)
                self.assertEqual(updated["skill_trace"][-1]["event"], "skill_evidence")


if __name__ == "__main__":
    unittest.main()
