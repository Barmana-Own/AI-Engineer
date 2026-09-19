import os
import tempfile
import unittest

from app.coordination.collaboration import CollaborationEngine
from app.coordination.models import (
    ConversationType,
    MeetingType,
    MessageType,
    WorkRequestStatus,
)
from app.coordination.store import list_messages
from app.db import connect, create_project, initialize_database
from app.coordination.collaboration_store import list_decisions, list_work_requests


class CollaborationTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.project = create_project("Collaboration", "structured collaboration", database_path=self.path)
        self.other = create_project("Other", "isolation", database_path=self.path)
        with connect(self.path) as database:
            for run_id, project_id in (("run-1", self.project["id"]), ("run-2", self.project["id"])):
                database.execute("INSERT INTO autonomy_runs(id, project_id, goal, requested_cycles, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'queued', datetime('now'), datetime('now'))", (run_id, project_id, "test", 1))
        self.engine = CollaborationEngine(self.path, max_rounds=2)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def test_scoped_messages_and_decision_resolution(self) -> None:
        conversation = self.engine.create_conversation(
            project_id=self.project["id"],
            run_id="run-1",
            subject="API design",
            conversation_type=ConversationType.GROUP,
            participants=("architect", "security", "engineering_manager"),
            topic="architecture",
        )
        self.engine.send(
            conversation_id=conversation["conversation_id"],
            sender_role="architect",
            message_type=MessageType.PROPOSAL,
            subject="proposal",
            body="Use a versioned API",
        )
        self.engine.send(
            conversation_id=conversation["conversation_id"],
            sender_role="security",
            message_type=MessageType.CHALLENGE,
            subject="risk",
            body="Require authentication",
        )
        messages = list_messages(
            project_id=self.project["id"],
            conversation_id=conversation["conversation_id"],
            database_path=self.path,
        )
        self.assertEqual([item["message_type"] for item in messages], ["PROPOSAL", "CHALLENGE"])
        self.assertEqual(self.engine.conversations(project_id=self.other["id"]), [])
        self.engine.resolve_discussion(
            conversation_id=conversation["conversation_id"],
            decision_maker="engineering_manager",
            title="API decision",
            decision="Use versioned API with authentication",
            evidence=("security-review",),
        )
        decisions = list_decisions(project_id=self.project["id"], database_path=self.path)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision_maker"], "engineering_manager")

    def test_discussion_round_limit(self) -> None:
        conversation = self.engine.create_conversation(
            project_id=self.project["id"],
            run_id="run-2",
            subject="debate",
            conversation_type=ConversationType.PROJECT,
            participants=("architect", "security"),
        )
        self.engine.discuss(
            conversation_id=conversation["conversation_id"],
            sender_role="architect",
            message_type=MessageType.PROPOSAL,
            subject="option",
            body="A",
        )
        self.engine.discuss(
            conversation_id=conversation["conversation_id"],
            sender_role="security",
            message_type=MessageType.CHALLENGE,
            subject="challenge",
            body="B",
        )
        with self.assertRaises(RuntimeError):
            self.engine.discuss(
                conversation_id=conversation["conversation_id"],
                sender_role="architect",
                message_type=MessageType.COUNTER_PROPOSAL,
                subject="counter",
                body="C",
            )

    def test_meeting_requires_output_and_persists_decision(self) -> None:
        meeting = self.engine.start_meeting(
            project_id=self.project["id"],
            meeting_type=MeetingType.ARCHITECTURE_REVIEW,
            objective="Choose API boundary",
            participants=("architect", "engineering_manager"),
            agenda=("contracts",),
        )
        self.engine.add_meeting_message(
            meeting_id=meeting["meeting_id"],
            sender_role="architect",
            message_type=MessageType.PROPOSAL,
            subject="contract",
            body="Keep gateway separate",
        )
        decision = self.engine.record_meeting_decision(
            meeting_id=meeting["meeting_id"],
            title="Gateway boundary",
            context="Architecture review",
            decision="Keep gateway separate",
            decision_maker="engineering_manager",
            evidence=("architecture.md",),
        )
        closed = self.engine.close_meeting(
            meeting["meeting_id"],
            action_items=("Add contract test",),
        )
        self.assertEqual(closed["status"], "completed")
        self.assertEqual(closed["decision_ids"], [decision["decision_id"]])
        self.assertEqual(len(self.engine.meetings(project_id=self.project["id"])), 1)

    def test_internal_request_lifecycle(self) -> None:
        request = self.engine.request_help(
            sender="tester",
            recipient="debugger",
            project_id=self.project["id"],
            request_type="debug",
            description="Investigate integration failure",
            priority=80,
        )
        answered = self.engine.respond_help(
            request["request_id"],
            response="Reproduced and fixed",
            status=WorkRequestStatus.ANSWERED,
        )
        self.assertEqual(answered["status"], "answered")
        requests = list_work_requests(project_id=self.project["id"], database_path=self.path)
        self.assertEqual(requests[0]["response"], "Reproduced and fixed")


if __name__ == "__main__":
    unittest.main()





