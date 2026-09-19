from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app import db
from app.coordination.incidents import (
    assign_incident_team,
    create_incident,
    create_postmortem,
    get_incident,
    get_postmortem,
    list_collaboration_quality,
    list_organizational_lessons,
    promote_postmortem_lesson,
    record_collaboration_issue,
    select_agent_for_role,
    transition_incident,
)
from app.coordination.owner_control import (
    create_project_opportunity,
    get_project_opportunity,
    list_project_opportunities,
    request_owner_action,
    resolve_owner_action,
)
from app.coordination.project_management import get_project_state
from app.db import create_project, initialize_database
from app.memory import MemoryStore
from app.organization.store import ensure_employee


class IncidentOwnerControlTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Incident Project", "workspace", database_path=self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def test_incident_lifecycle_team_postmortem_and_lesson(self) -> None:
        incident = create_incident(
            self.project["id"],
            "Critical integration failure",
            "critical_test_failure",
            description="The release test suite failed.",
            impact="Release blocked.",
            database_path=self.path,
        )
        self.assertEqual(incident["phase"], "detect")
        team = assign_incident_team(
            incident["incident_id"],
            roles=("incident_manager", "debugger", "tester"),
            database_path=self.path,
        )
        self.assertEqual({item["role"] for item in team}, {"incident_manager", "debugger", "tester"})
        for phase in ("contain", "diagnose", "repair", "verify"):
            transition_incident(incident["incident_id"], phase, actor_role="incident_manager", evidence=(phase,), database_path=self.path)
        postmortem = create_postmortem(
            incident["incident_id"],
            what_happened="A migration was not applied in the test database.",
            impact="Release verification failed.",
            timeline=("test failed", "migration applied"),
            root_cause="Database initialization drift.",
            contributing_factors=("Missing migration check",),
            repair="Applied migration and added a clean-database test.",
            verification=("orchestrator tests",),
            prevention_ideas=("Run migrations in CI",),
            follow_up_tasks=("Add migration smoke test",),
            database_path=self.path,
        )
        self.assertEqual(get_postmortem(postmortem["postmortem_id"], database_path=self.path)["root_cause"], "Database initialization drift.")
        lesson = promote_postmortem_lesson(
            postmortem["postmortem_id"],
            summary="Database schema changes require migration tests.",
            evidence=({"type": "tests_passed", "tests": "migration smoke"},),
            database_path=self.path,
        )
        self.assertEqual(lesson["lifecycle"], "validated")
        transition_incident(incident["incident_id"], "postmortem", database_path=self.path)
        transition_incident(incident["incident_id"], "learn", database_path=self.path)
        resolved = transition_incident(incident["incident_id"], "resolved", database_path=self.path)
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(len(list_organizational_lessons(database_path=self.path)), 1)
        self.assertEqual(get_incident(incident["incident_id"], database_path=self.path)["phase"], "resolved")

    def test_team_selection_uses_performance_and_collaboration_quality(self) -> None:
        ensure_employee("backend", agent_id="backend-fastapi", model_profile="fastapi", database_path=self.path)
        ensure_employee("backend", agent_id="backend-generic", model_profile="generic", database_path=self.path)
        memory = MemoryStore(self.path)
        for _ in range(3):
            memory.record_agent_outcome(
                role="backend",
                model_profile="fastapi",
                domain="fastapi",
                success=True,
                tests_passed=True,
                review_accepted=True,
                successful_domain="fastapi",
            )
        memory.record_agent_outcome(
            role="backend",
            model_profile="generic",
            domain="fastapi",
            success=False,
            tests_passed=False,
            review_accepted=False,
            retries=2,
        )
        selected = select_agent_for_role("backend", domain="fastapi", database_path=self.path)
        self.assertEqual(selected["agent_id"], "backend-fastapi")
        quality = record_collaboration_issue("dependency_mistake", "missing_migration", project_id=self.project["id"], example="migration dependency", database_path=self.path)
        record_collaboration_issue("dependency_mistake", "missing_migration", project_id=self.project["id"], example="second occurrence", database_path=self.path)
        self.assertEqual(quality["occurrences"], 1)
        self.assertEqual(list_collaboration_quality(project_id=self.project["id"], database_path=self.path)[0]["occurrences"], 2)

    def test_owner_pause_resume_priority_and_high_risk_approval(self) -> None:
        started = request_owner_action("start_project", project_id=self.project["id"], database_path=self.path)
        self.assertEqual(started["status"], "applied")
        self.assertEqual(get_project_state(self.project["id"], database_path=self.path)["phase"], "requirements")
        paused = request_owner_action("pause_project", project_id=self.project["id"], database_path=self.path)
        self.assertEqual(paused["status"], "applied")
        self.assertEqual(get_project_state(self.project["id"], database_path=self.path)["phase"], "paused")
        resumed = request_owner_action("resume_project", project_id=self.project["id"], payload={"resume_phase": "requirements"}, database_path=self.path)
        self.assertEqual(resumed["status"], "applied")
        priority = request_owner_action("change_priority", project_id=self.project["id"], payload={"priority": 90}, database_path=self.path)
        self.assertEqual(priority["result"]["priority"], 90)
        high_risk = request_owner_action("production_deployment", project_id=self.project["id"], reason="release", database_path=self.path)
        self.assertEqual(high_risk["status"], "pending_approval")
        approved = resolve_owner_action(high_risk["action_id"], approved=True, database_path=self.path)
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["result"]["execution"], "requires_explicit_external_operator")

    def test_external_opportunity_is_persisted_without_platform_automation(self) -> None:
        opportunity = create_project_opportunity(
            source="future_adapter",
            external_ref="opp-1",
            title="API modernization",
            summary="Potential backend modernization project",
            requirements=("FastAPI", "tests"),
            database_path=self.path,
        )
        self.assertEqual(get_project_opportunity(opportunity["opportunity_id"], database_path=self.path)["status"], "inbox")
        self.assertEqual(len(list_project_opportunities(source="future_adapter", database_path=self.path)), 1)


if __name__ == "__main__":
    unittest.main()
