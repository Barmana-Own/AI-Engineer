from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.coordination.company_trace import build_company_trace, list_events, run_company_simulation
from app.db import initialize_database


class CompanyTraceIntegrationTests(unittest.TestCase):
    def test_company_simulation_persists_end_to_end_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="company-trace-") as directory:
            root = Path(directory)
            database = root / "company.sqlite3"
            workspace = root / "workspace"
            output = root / "trace"
            trace = run_company_simulation(database, workspace, output_dir=output)
            project_id = str(trace["project"]["id"])
            run_id = str(trace["run_id"])

            self.assertEqual(trace["project"]["phase"], "completed")
            self.assertTrue(trace["team"]["team_members"])
            event_types = {str(event["event_type"]) for event in trace["events"]}
            for event_type in {
                "PROJECT_CREATED",
                "TEAM_CREATED",
                "AGENT_ASSIGNED",
                "TASK_ASSIGNED",
                "MESSAGE_SENT",
                "MEETING_STARTED",
                "DECISION_MADE",
                "INCIDENT_OPENED",
                "INTERNAL_REQUEST_CREATED",
                "TEST_EXECUTED",
                "TEST_FAILED",
                "REVIEW_REJECTED",
                "HANDOFF_CREATED",
                "ORCHESTRATOR_RESTARTED",
                "RECOVERY_RESUMED",
                "LESSON_CAPTURED",
                "RELEASE_READY",
                "PROJECT_COMPLETED",
            }:
                self.assertIn(event_type, event_types)
            message_types = {str(message["message_type"]) for message in trace["messages"]}
            self.assertTrue({"PROPOSAL", "CHALLENGE", "EVIDENCE", "COUNTER_PROPOSAL"}.issubset(message_types))
            self.assertTrue(trace["decisions"])
            self.assertTrue(trace["meetings"])
            self.assertTrue(trace["internal_requests"])
            self.assertTrue(trace["handoffs"])
            self.assertTrue(trace["incidents"])
            self.assertTrue(trace["postmortems"])
            self.assertTrue(trace["memories"])
            self.assertTrue(trace["trace_artifacts"]["json"])
            self.assertTrue(Path(trace["trace_artifacts"]["json"]).exists())
            self.assertTrue(Path(trace["trace_artifacts"]["markdown"]).exists())

            initialize_database(database)
            resumed = build_company_trace(project_id, run_id=run_id, database_path=database)
            self.assertEqual(len(resumed["events"]), len(trace["events"]))
            self.assertEqual(len(resumed["tasks"]), len(trace["tasks"]))
            self.assertTrue(any(event["event_type"] == "RECOVERY_RESUMED" for event in resumed["events"]))

    def test_company_events_are_project_scoped_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="company-events-") as directory:
            database = Path(directory) / "company.sqlite3"
            initialize_database(database)
            from app.db import create_project

            first = create_project("First", str(Path(directory) / "first"), database_path=database)
            second = create_project("Second", str(Path(directory) / "second"), database_path=database)
            event_id = "stable-event"
            first_event = __import__("app.coordination.company_trace", fromlist=["emit_event"]).emit_event(
                "PROJECT_CREATED", project_id=first["id"], event_id=event_id, payload={"token": "do-not-persist"}, database_path=database
            )
            duplicate = __import__("app.coordination.company_trace", fromlist=["emit_event"]).emit_event(
                "PROJECT_CREATED", project_id=first["id"], event_id=event_id, payload={"changed": True}, database_path=database
            )
            self.assertEqual(first_event["event_id"], duplicate["event_id"])
            self.assertEqual(1, len(list_events(project_id=first["id"], database_path=database)))
            self.assertEqual([], list_events(project_id=second["id"], database_path=database))
            self.assertNotIn("do-not-persist", str(first_event))


if __name__ == "__main__":
    unittest.main()
