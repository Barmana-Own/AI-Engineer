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
    build_skill_evidence,
    effective_tool_permissions,
    evaluate_quality_gates,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class SkillAwareScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SkillRegistry(REPOSITORY_ROOT)
        cls.router = SkillRouter(cls.registry)

    def _project_plan(self, objective: str, project_type: str):
        return self.router.route_project(
            SkillRouteRequest(
                task_objective=objective,
                assigned_role="project_manager",
                project_type=project_type,
                project_id=f"project-{project_type}",
            )
        )

    def _run_task(
        self,
        *,
        project_id: str,
        task_id: str,
        role: str,
        objective: str,
        project_type: str,
        requirements: tuple[str, ...] = (),
        risk: str = "",
        technologies: tuple[str, ...] = (),
    ) -> dict[str, object]:
        route = self.router.route(
            SkillRouteRequest(
                task_objective=objective,
                assigned_role=role,
                project_type=project_type,
                requirements=requirements,
                risk=risk,
                technologies=technologies,
                task_id=task_id,
                project_id=project_id,
            )
        )
        selected_ids = set(route.skill_ids)
        reference_names = {
            skill_id: (self.registry.get(skill_id).references[0],)
            for skill_id in route.skill_ids
            if self.registry.get(skill_id).references
        }
        loaded = SkillContextLoader(self.registry).load(
            route,
            task_id=task_id,
            role=role,
            project_id=project_id,
            reference_names=reference_names,
        )
        allowed = set()
        for skill_id in route.skill_ids:
            allowed.update(self.registry.get(skill_id).allowed_tools)
        # This fixture models a worker that has broad task tools. The
        # effective set is still bounded by the selected skill contracts.
        permissions = effective_tool_permissions(
            role_tools=allowed,
            task_tools=allowed,
            global_tools=allowed,
            selected_skill_ids=route.skill_ids,
            registry=self.registry,
        )

        task = db.create_task(project_id, objective)
        route_trace = {
            "event": "skill_route",
            "task_id": task_id,
            "agent_id": f"{role}-agent",
            "role": route.role,
            "skill_ids": list(route.skill_ids),
            "stage_dependencies": [item.as_dict() for item in route.stage_dependencies],
            "worker_context": {
                "references_loaded": {
                    item.skill_id: sorted(item.references)
                    for item in loaded
                },
                "skill_documents_loaded": [item.skill_id for item in loaded],
                "tools_allowed": sorted(permissions),
            },
        }
        db.set_task_skill_route(
            task["id"],
            [selection.as_dict() for selection in route.selections],
            trace=[route_trace],
        )

        evidence_by_skill: dict[str, dict[str, object]] = {}
        for skill_id in route.skill_ids:
            evidence: dict[str, object] = {"checks_run": [f"scenario:{task_id}"]}
            if skill_id == "software-testing":
                evidence["tests_passed"] = True
            elif skill_id == "qa-debugging":
                evidence["regressions_absent"] = True
            elif skill_id in {"authentication-authorization", "application-security"}:
                evidence["security_findings_resolved"] = True
            elif skill_id == "deployment-production":
                evidence["health_checks_passed"] = True
            elif skill_id == "fullstack-final-review":
                evidence["review_accepted"] = True
                evidence["critical_findings_absent"] = True
            evidence_by_skill[skill_id] = evidence
            db.append_task_skill_evidence(
                task["id"],
                build_skill_evidence(
                    skill_id=skill_id,
                    task_id=task_id,
                    agent_id=f"{role}-agent",
                    checks_run=evidence["checks_run"],
                    gate_status="passed",
                    evidence=(
                        {"source": "deterministic_skill_scenario", "verified": True},
                    ),
                ),
            )

        gates = evaluate_quality_gates(route.selections, evidence_by_skill)
        persisted = db.get_task(task["id"])
        assert persisted is not None
        return {
            "task_id": task["id"],
            "role": route.role,
            "skill_ids": selected_ids,
            "loaded_ids": {item.skill_id for item in loaded},
            "references_loaded": {
                item.skill_id: set(item.references) for item in loaded
            },
            "tools": permissions,
            "gates": gates,
            "trace": persisted["skill_trace"],
        }

    def test_scenarios_route_only_relevant_skills_and_persist_worker_trace(self) -> None:
        scenarios = {
            "A": {
                "objective": "Build a small full-stack application with authentication, API, frontend, tests, and documentation.",
                "project_type": "full-stack",
                "required": {
                    "project-analysis-prompt-engineering",
                    "design-system-ui-architecture",
                    "frontend-architecture",
                    "backend-architecture",
                    "database-architecture",
                    "api-integration",
                    "authentication-authorization",
                    "application-security",
                    "software-testing",
                    "qa-debugging",
                    "fullstack-final-review",
                },
                "forbidden": {"deployment-production"},
                "tasks": (
                    ("project_manager", "Define milestones and dependencies for the full-stack application."),
                    ("requirements", "Clarify authentication acceptance criteria and scope."),
                    ("architect", "Design frontend, backend, API, and database boundaries for the application."),
                    ("backend", "Implement the authenticated API and persistence layer."),
                    ("frontend", "Implement the responsive frontend and API integration."),
                    ("security", "Review authentication and authorization threat controls."),
                    ("tester", "Run application tests and report regressions."),
                    ("reviewer", "Review the full-stack implementation and authentication evidence."),
                    ("release_verifier", "Verify acceptance criteria and test evidence."),
                ),
            },
            "B": {
                "objective": "Fix a transaction migration defect in an existing backend and add regression tests.",
                "project_type": "backend-only",
                "required": {
                    "project-analysis-prompt-engineering",
                    "backend-architecture",
                    "database-architecture",
                    "software-testing",
                    "qa-debugging",
                    "fullstack-final-review",
                },
                "forbidden": {
                    "design-system-ui-architecture",
                    "frontend-architecture",
                    "deployment-production",
                },
                "tasks": (
                    ("project_manager", "Plan the backend migration repair and dependencies."),
                    ("backend", "Fix the transaction migration defect in the backend database."),
                    ("tester", "Run regression tests for the transaction migration."),
                    ("debugger", "Reproduce and repair the failing migration regression."),
                    ("reviewer", "Review the backend migration fix and test evidence."),
                ),
            },
            "C": {
                "objective": "Implement a frontend accessibility improvement with responsive tests.",
                "project_type": "frontend-only",
                "required": {
                    "design-system-ui-architecture",
                    "frontend-architecture",
                    "software-testing",
                },
                "forbidden": {
                    "backend-architecture",
                    "database-architecture",
                    "authentication-authorization",
                    "application-security",
                    "deployment-production",
                },
                "tasks": (
                    ("frontend", "Implement the accessible responsive React layout."),
                    ("tester", "Run frontend accessibility and regression tests."),
                ),
            },
            "D": {
                "objective": "Fix an authentication authorization security issue with tests and debugging.",
                "project_type": "security-fix",
                "required": {
                    "authentication-authorization",
                    "application-security",
                    "software-testing",
                    "qa-debugging",
                    "fullstack-final-review",
                },
                "forbidden": {
                    "design-system-ui-architecture",
                    "frontend-architecture",
                    "database-architecture",
                    "deployment-production",
                },
                "tasks": (
                    ("security", "Review and remediate the authentication authorization boundary."),
                    ("tester", "Run security regression tests."),
                    ("debugger", "Reproduce and repair the authentication security defect."),
                    ("reviewer", "Independently review the authentication security fix."),
                ),
            },
            "E": {
                "objective": "Prepare a release with regression tests, QA, deployment health checks, and final review.",
                "project_type": "release",
                "required": {
                    "software-testing",
                    "qa-debugging",
                    "deployment-production",
                    "fullstack-final-review",
                },
                "forbidden": {
                    "design-system-ui-architecture",
                    "frontend-architecture",
                    "backend-architecture",
                    "database-architecture",
                },
                "tasks": (
                    ("tester", "Run the release regression test plan."),
                    ("debugger", "Resolve any release QA regression."),
                    ("devops", "Execute release build and deployment health checks."),
                    ("release_verifier", "Perform independent deployment and final release verification."),
                    ("reviewer", "Perform an independent final review of release evidence."),
                ),
            },
        }

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory) / "phase10d.db"
            with patch.object(db, "DATABASE_PATH", database_path):
                db.initialize_database()
                for scenario_id, scenario in scenarios.items():
                    project = db.create_project(
                        f"Phase 10D Scenario {scenario_id}",
                        str(scenario["objective"]),
                    )
                    project_plan = self._project_plan(
                        str(scenario["objective"]),
                        str(scenario["project_type"]),
                    )
                    self.assertTrue(
                        set(scenario["required"]).issubset(set(project_plan.skill_ids)),
                        scenario_id,
                    )
                    self.assertTrue(
                        set(scenario["forbidden"]).isdisjoint(set(project_plan.skill_ids)),
                        scenario_id,
                    )
                    union: set[str] = set()
                    for index, (role, objective) in enumerate(scenario["tasks"], start=1):
                        result = self._run_task(
                            project_id=project["id"],
                            task_id=f"{scenario_id}-task-{index}",
                            role=role,
                            objective=objective,
                            project_type=str(scenario["project_type"]),
                        )
                        union.update(result["skill_ids"])
                        self.assertEqual(result["skill_ids"], result["loaded_ids"])
                        self.assertTrue(
                            all(gate.status == "passed" for gate in result["gates"]),
                            (scenario_id, role),
                        )
                        self.assertEqual(result["trace"][0]["event"], "skill_route")
                        self.assertEqual(
                            sorted(result["trace"][0]["worker_context"]["skill_documents_loaded"]),
                            sorted(result["loaded_ids"]),
                        )
                        self.assertTrue(
                            all(len(refs) <= 1 for refs in result["references_loaded"].values())
                        )
                    self.assertTrue(
                        set(scenario["required"]).issubset(union),
                        (scenario_id, sorted(union)),
                    )

    def test_lazy_context_and_quality_gate_proof(self) -> None:
        route = self.router.route(
            SkillRouteRequest(
                task_objective="Implement a responsive React accessibility component.",
                assigned_role="frontend",
                project_type="frontend-only",
                task_id="context-task",
                project_id="context-project",
            )
        )
        first_reference = self.registry.get("frontend-architecture").references[0]
        loaded = SkillContextLoader(self.registry).load(
            route,
            task_id="context-task",
            role="frontend",
            project_id="context-project",
            reference_names={"frontend-architecture": (first_reference,)},
        )
        self.assertEqual({item.skill_id for item in loaded}, set(route.skill_ids))
        self.assertEqual(
            set(next(item for item in loaded if item.skill_id == "frontend-architecture").references),
            {first_reference},
        )
        self.assertNotIn("backend-architecture", {item.skill_id for item in loaded})
        self.assertNotIn("deployment-production", {item.skill_id for item in loaded})
        blocked = evaluate_quality_gates(route.selections, {})
        self.assertTrue(blocked)
        self.assertTrue(all(item.status == "blocked" for item in blocked))

    def test_independent_release_review_has_read_only_effective_tools(self) -> None:
        reviewer_route = self.router.route(
            SkillRouteRequest(
                task_objective="Review release evidence for an authentication fix.",
                assigned_role="reviewer",
                project_type="security-fix",
                task_id="review-task",
                project_id="review-project",
            )
        )
        reviewer_tools = effective_tool_permissions(
            role_tools={"read_file", "list_files", "search", "diff", "safe_validation", "evidence_write"},
            task_tools={"read_file", "list_files", "search", "diff", "safe_validation", "evidence_write"},
            global_tools={"read_file", "list_files", "search", "diff", "safe_validation", "evidence_write"},
            selected_skill_ids=reviewer_route.skill_ids,
            registry=self.registry,
        )
        self.assertIn("fullstack-final-review", reviewer_route.skill_ids)
        self.assertNotIn("fixture_write", reviewer_tools)
        self.assertNotIn("release_artifact_write", reviewer_tools)
        self.assertNotIn("run_terminal", reviewer_tools)


if __name__ == "__main__":
    unittest.main()
