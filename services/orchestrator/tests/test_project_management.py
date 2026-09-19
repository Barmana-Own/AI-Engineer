import os
import tempfile
import unittest

from app.db import create_project, initialize_database
from app.coordination import store
from app.coordination.models import CoordinationTask, TaskState
from app.coordination.project_management import (
    ProjectManager,
    ProjectPhase,
    blackboard,
    claim_next_work,
    complete_work,
    create_milestone,
    create_risk,
    enqueue_work,
    list_quality_gates,
    schedule_ready_tasks,
    set_quality_gate,
    transition_project_phase,
)


class ProjectManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.path)
        initialize_database(self.path)
        self.first = create_project("First", "first", database_path=self.path)
        self.second = create_project("Second", "second", database_path=self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def test_lifecycle_quality_gate_and_evidence(self) -> None:
        project_id = self.first["id"]
        set_quality_gate(project_id, "requirements_ready", status="passed", evidence=["requirements.md"], database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.REQUIREMENTS, database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.ARCHITECTURE, database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.IMPLEMENTATION, database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.INTEGRATION, database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.TESTING, database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.REVIEW, database_path=self.path)
        set_quality_gate(project_id, "tests_passed", status="passed", evidence=["pytest"], database_path=self.path)
        set_quality_gate(project_id, "review_accepted", status="passed", evidence=["review"], database_path=self.path)
        set_quality_gate(project_id, "security_review", status="waived", evidence=["not security sensitive"], database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.SECURITY_REVIEW, database_path=self.path)
        transition_project_phase(project_id, ProjectPhase.RELEASE_VERIFICATION, evidence=["release checklist"], database_path=self.path)
        with self.assertRaises(ValueError):
            transition_project_phase(project_id, ProjectPhase.COMPLETED, database_path=self.path)
        completed = transition_project_phase(project_id, ProjectPhase.COMPLETED, evidence=["acceptance criteria verified"], database_path=self.path)
        self.assertEqual(completed["phase"], ProjectPhase.COMPLETED.value)
        self.assertEqual(len(list_quality_gates(project_id, database_path=self.path)), 4)

    def test_milestones_risks_and_project_isolation(self) -> None:
        create_milestone(self.first["id"], "M1", deliverables=["api"], database_path=self.path)
        create_risk(self.first["id"], "dependency", severity="high", database_path=self.path)
        board = blackboard(database_path=self.path)
        self.assertEqual(len(board["active_projects"]), 2)
        self.assertEqual(len(board["open_risks"]), 1)
        scoped = blackboard(project_id=self.second["id"], database_path=self.path)
        self.assertEqual(scoped["open_risks"], [])
        self.assertEqual(scoped["project_phases"], {self.second["id"]: "intake"})

    def test_queue_claim_completion_and_priority(self) -> None:
        low = enqueue_work("implementer", self.first["id"], "task", "low", priority=10, database_path=self.path)
        high = enqueue_work("implementer", self.first["id"], "task", "high", priority=90, database_path=self.path)
        claimed = claim_next_work("implementer", project_id=self.first["id"], database_path=self.path)
        self.assertEqual(claimed["queue_id"], high["queue_id"])
        completed = complete_work(claimed["queue_id"], database_path=self.path)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(claim_next_work("implementer", project_id=self.first["id"], database_path=self.path)["queue_id"], low["queue_id"])

    def test_dependency_scheduler_blocks_until_dependency(self) -> None:
        upstream = CoordinationTask(project_id=self.first["id"], title="design", description="design", role="architect", state=TaskState.PENDING)
        store.create_task(upstream, database_path=self.path)
        downstream = CoordinationTask(project_id=self.first["id"], title="implement", description="implement", role="backend", state=TaskState.PENDING, dependencies=(upstream.id,))
        store.create_task(downstream, database_path=self.path)
        ready = schedule_ready_tasks(project_id=self.first["id"], database_path=self.path)
        self.assertEqual([item["item_ref"] for item in ready], [upstream.id])
        store.transition(upstream.id, TaskState.ASSIGNED, database_path=self.path); store.transition(upstream.id, TaskState.RUNNING, database_path=self.path); store.transition(upstream.id, TaskState.COMPLETED, database_path=self.path)
        ready = schedule_ready_tasks(project_id=self.first["id"], database_path=self.path)
        self.assertEqual([item["item_ref"] for item in ready], [downstream.id])

    def test_resource_lock_prevents_two_writers(self) -> None:
        task_a = CoordinationTask(project_id=self.first["id"], title="a", description="a", role="backend")
        task_b = CoordinationTask(project_id=self.first["id"], title="b", description="b", role="frontend")
        store.create_task(task_a, database_path=self.path)
        store.create_task(task_b, database_path=self.path)
        self.assertTrue(store.acquire_lock("workspace:first", task_a.id, "backend", database_path=self.path))
        self.assertFalse(store.acquire_lock("workspace:first", task_b.id, "frontend", database_path=self.path))



    def test_implementation_requires_requirements_gate(self) -> None:
        project_id = self.first["id"]
        transition_project_phase(project_id, ProjectPhase.REQUIREMENTS, database_path=self.path)
        with self.assertRaises(ValueError):
            transition_project_phase(project_id, ProjectPhase.IMPLEMENTATION, database_path=self.path)


    def test_release_verification_requires_test_and_review_gates(self) -> None:
        project_id = self.first["id"]
        set_quality_gate(project_id, "requirements_ready", status="passed", database_path=self.path)
        for phase in (ProjectPhase.REQUIREMENTS, ProjectPhase.ARCHITECTURE, ProjectPhase.IMPLEMENTATION, ProjectPhase.INTEGRATION, ProjectPhase.TESTING, ProjectPhase.REVIEW):
            transition_project_phase(project_id, phase, database_path=self.path)
        with self.assertRaises(ValueError):
            transition_project_phase(project_id, ProjectPhase.RELEASE_VERIFICATION, database_path=self.path)
        set_quality_gate(project_id, "tests_passed", status="passed", evidence=["pytest"], database_path=self.path)
        set_quality_gate(project_id, "review_accepted", status="passed", evidence=["review"], database_path=self.path)
        released = transition_project_phase(project_id, ProjectPhase.RELEASE_VERIFICATION, evidence=["release checklist"], database_path=self.path)
        self.assertEqual(released["phase"], ProjectPhase.RELEASE_VERIFICATION.value)

    def test_scheduler_skips_conflicting_writer_resource(self) -> None:
        blocker = CoordinationTask(project_id=self.first["id"], title="blocker", description="lock holder", role="backend")
        writer = CoordinationTask(project_id=self.first["id"], title="writer", description="conflicting writer", role="backend", scope=("workspace:first",), writer=True)
        store.create_task(blocker, database_path=self.path)
        store.create_task(writer, database_path=self.path)
        store.transition(blocker.id, TaskState.READY, database_path=self.path)
        store.transition(blocker.id, TaskState.ASSIGNED, database_path=self.path)
        store.transition(blocker.id, TaskState.RUNNING, database_path=self.path)
        self.assertTrue(store.acquire_lock("workspace:first", blocker.id, "backend", database_path=self.path))
        ready = schedule_ready_tasks(project_id=self.first["id"], database_path=self.path)
        self.assertNotIn(writer.id, [item["item_ref"] for item in ready])
    def test_project_manager_facade_tracks_delivery_state(self) -> None:
        manager = ProjectManager(database_path=self.path)
        milestone = manager.add_milestone(self.first["id"], "delivery", deliverables=["report"])
        self.assertEqual(milestone["project_id"], self.first["id"])
        report = manager.status(self.first["id"])
        self.assertEqual(report["project"]["id"], self.first["id"])
    def test_review_rejection_reopens_implementation(self) -> None:
        project_id = self.first["id"]
        set_quality_gate(project_id, "requirements_ready", status="passed", database_path=self.path)
        for phase in (ProjectPhase.REQUIREMENTS, ProjectPhase.ARCHITECTURE, ProjectPhase.IMPLEMENTATION, ProjectPhase.INTEGRATION, ProjectPhase.TESTING, ProjectPhase.REVIEW):
            transition_project_phase(project_id, phase, database_path=self.path)
        rejected = set_quality_gate(project_id, "review_accepted", status="failed", evidence=["review feedback"], database_path=self.path)
        self.assertEqual(rejected["status"], "failed")
        state = ProjectManager(database_path=self.path).status(project_id)["project"]
        self.assertEqual(state["phase"], ProjectPhase.IMPLEMENTATION.value)
if __name__ == "__main__":

    unittest.main()







