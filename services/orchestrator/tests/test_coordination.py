from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import create_project, initialize_database
from app.coordination import (
    AgentHandoff,
    MessageType,
    ROLE_REGISTRY,
    TaskState,
    get_role_contract,
)
from app.coordination import store
from app.coordination.supervisor import Supervisor
from app.coordination.bus import DiscussionController, MessageBus
from app.coordination.models import CoordinationTask
from app.coordination.scheduler import DependencyScheduler


class CoordinationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "coordination.db"
        initialize_database(self.db)
        self.project = create_project("coordination-test", self.temp.name, database_path=self.db)
        self.project_id = str(self.project["id"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_role_registry_exposes_canonical_contracts_and_aliases(self) -> None:
        required = {"supervisor", "requirements", "planner", "architect", "researcher", "backend", "frontend", "implementer", "tester", "debugger", "reviewer", "security", "integration", "docs", "release_verifier"}
        self.assertTrue(required <= set(ROLE_REGISTRY))
        contract = get_role_contract("verifier")
        self.assertEqual(contract.id, "tester")
        self.assertTrue(contract.output_contract)
        self.assertIsNotNone(contract.escalation_rules)

    def test_dependencies_parallelism_and_writer_lock(self) -> None:
        parent = CoordinationTask(project_id=self.project_id, title="architecture", description="design", role="architect", scope=("src/api",), writer=True)
        independent = CoordinationTask(project_id=self.project_id, title="research", description="inspect", role="researcher", scope=("docs",), writer=False)
        child = CoordinationTask(project_id=self.project_id, title="implementation", description="build", role="backend", dependencies=(parent.id,), scope=("src/api",), writer=True)
        for task in (parent, independent, child):
            store.create_task(task, database_path=self.db)
        scheduler = DependencyScheduler(self.db)
        batches = scheduler.ready_batches(project_id=self.project_id)
        self.assertEqual({str(item["id"]) for batch in batches for item in batch}, {parent.id, independent.id})
        self.assertEqual(store.get_task(child.id, database_path=self.db)["state"], TaskState.PENDING.value)
        scheduler.assign(parent.id, "architect")
        scheduler.start(parent.id)
        self.assertFalse(store.acquire_lock("src/api", "other-task", "backend", database_path=self.db))
        scheduler.finish(parent.id, success=True)
        scheduler.complete_review(parent.id, True)
        self.assertTrue(store.acquire_lock("src/api", "other-task", "backend", database_path=self.db))
        store.release_lock("src/api", "other-task", database_path=self.db)
        refreshed = scheduler.refresh(project_id=self.project_id)
        self.assertTrue(any(str(item["id"]) == child.id and item["state"] == TaskState.READY.value for item in refreshed))

    def test_message_handoff_and_bounded_discussion(self) -> None:
        bus = MessageBus(self.db)
        message = bus.publish(sender_role="architect", recipient_role="reviewer", message_type=MessageType.PROPOSAL, subject="API", body="Use a versioned route", project_id=self.project_id)
        self.assertEqual(message["message_type"], MessageType.PROPOSAL.value)
        discussion = DiscussionController(bus, max_rounds=2)
        run_id = str(Supervisor(self.db).start_objective(project_id=self.project_id, objective="Discuss an API")["run_id"])
        discussion.submit(sender_role="architect", message_type=MessageType.PROPOSAL, subject="choice", body="A", run_id=run_id, project_id=self.project_id)
        discussion.submit(sender_role="reviewer", message_type=MessageType.CHALLENGE, subject="choice", body="B", run_id=run_id, project_id=self.project_id)
        with self.assertRaises(RuntimeError):
            discussion.submit(sender_role="architect", message_type=MessageType.ANSWER, subject="choice", body="C", run_id=run_id, project_id=self.project_id)
        decision = discussion.resolve(run_id=run_id, project_id=self.project_id, subject="choice", decision="Supervisor selects A")
        self.assertEqual(decision["message_type"], MessageType.DECISION.value)
        handoff = AgentHandoff(sender_role="architect", recipient_role="backend", summary="API contract ready", completed=("contract",), changed_files=("openapi.yaml",), project_id=self.project_id, run_id=run_id)
        persisted = store.create_handoff(handoff, database_path=self.db)
        self.assertEqual(persisted["recipient_role"], "backend")
        self.assertEqual(len(store.list_handoffs(project_id=self.project_id, database_path=self.db)), 1)

    def test_supervisor_delegates_dag_and_completes_simulated_workflow(self) -> None:
        supervisor = Supervisor(self.db)
        started = supervisor.start_objective(project_id=self.project_id, objective="Add a small API endpoint and tests")
        self.assertEqual(len(started["tasks"]), 10)
        guard = 0
        while guard < 30:
            batches = supervisor.next_ready(run_id=str(started["run_id"]), project_id=self.project_id)
            if not batches:
                break
            for batch in batches:
                for task in batch:
                    supervisor.record_result(str(task["id"]), summary="validated", evidence=["unit-test"], approved=True)
            guard += 1
        status = supervisor.status(str(started["run_id"]))
        self.assertTrue(status["complete"], status)
        self.assertEqual(status["states"][TaskState.COMPLETED.value], 10)
        self.assertGreaterEqual(len(status["messages"]), 11)

    def test_failure_records_evidence_and_retries(self) -> None:
        supervisor = Supervisor(self.db, max_retries=1)
        started = supervisor.start_objective(project_id=self.project_id, objective="Retry a task")
        task = supervisor.next_ready(run_id=str(started["run_id"]), project_id=self.project_id)[0][0]
        failed = supervisor.record_failure(str(task["id"]), reason="temporary provider failure")
        self.assertEqual(failed["state"], TaskState.FAILED.value)
        self.assertEqual(failed["retry_count"], 1)
        retried = supervisor.next_ready(run_id=str(started["run_id"]), project_id=self.project_id)
        self.assertTrue(retried)
        self.assertEqual(retried[0][0]["id"], task["id"])


if __name__ == "__main__":
    unittest.main()





