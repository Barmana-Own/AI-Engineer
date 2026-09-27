from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app import db
from app.recovery import (
    LeaseConflictError,
    acquire_task_lease,
    classify_dependency_error,
    classify_task,
    get_recovery_status,
    heartbeat_task_lease,
    pause_task_for_dependency,
    recover_incomplete_runs,
    release_task_lease,
    resume_run,
)


class DurableRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "recovery.db"
        self._database_patch = patch.object(db, "DATABASE_PATH", self.database_path)
        self._database_patch.start()
        db.initialize_database()
        self.project = db.create_project("Recovery", str(Path(self._temporary_directory.name) / "workspace"))

    def tearDown(self) -> None:
        self._database_patch.stop()
        self._temporary_directory.cleanup()

    def _task(self, *, status: str = "queued", run_id: str | None = None) -> dict:
        task = db.create_task(self.project["id"], "durable task", mode="autonomous")
        changes = {"status": status}
        if run_id:
            changes["run_id"] = run_id
        return db.update_task(task["id"], **changes)

    def test_lease_is_idempotent_and_protects_single_writer(self) -> None:
        task = self._task()
        first = acquire_task_lease(task["id"], owner_id="worker-a", ttl_seconds=60)
        second = acquire_task_lease(task["id"], owner_id="worker-a", ttl_seconds=60)
        self.assertEqual(first["lease_token"], second["lease_token"])
        with self.assertRaises(LeaseConflictError):
            acquire_task_lease(task["id"], owner_id="worker-b", ttl_seconds=60)
        self.assertTrue(heartbeat_task_lease(task["id"], first["lease_token"]))
        self.assertTrue(release_task_lease(task["id"], first["lease_token"]))
        third = acquire_task_lease(task["id"], owner_id="worker-b", ttl_seconds=60)
        self.assertEqual(third["owner_id"], "worker-b")

    def test_expired_lease_can_be_taken_over(self) -> None:
        task = self._task()
        acquire_task_lease(task["id"], owner_id="worker-a", ttl_seconds=60)
        old = "2020-01-01T00:00:00+00:00"
        with db.connect() as connection:
            connection.execute("UPDATE execution_leases SET expires_at = ? WHERE task_id = ?", (old, task["id"]))
            connection.execute("UPDATE agent_tasks SET lease_expires_at = ?, heartbeat_at = ? WHERE id = ?", (old, old, task["id"]))
        takeover = acquire_task_lease(task["id"], owner_id="worker-b", ttl_seconds=60)
        self.assertEqual(takeover["owner_id"], "worker-b")

    def test_dependency_pause_redacts_error_and_can_be_requeued(self) -> None:
        task = self._task()
        paused = pause_task_for_dependency(task["id"], "provider", "provider timeout api_key=super-secret-token", provider="primary", fallback_provider="secondary", retry_after_seconds=1)
        self.assertEqual(paused["status"], "waiting_provider")
        self.assertNotIn("super-secret-token", paused["error"])
        self.assertEqual(classify_dependency_error("model gateway timeout")[0], "provider")
        requeued = db.update_task(task["id"], retry_after="2000-01-01T00:00:00+00:00")
        from app.recovery import requeue_waiting_task
        ready = requeue_waiting_task(requeued["id"])
        self.assertTrue(ready)
        self.assertEqual(db.get_task(requeued["id"])["status"], "queued")

    def test_startup_recovery_classifies_safe_and_verification_tasks(self) -> None:
        safe_run = db.create_autonomy_run(self.project["id"], "safe", 1)
        safe_task = self._task(run_id=safe_run["id"])
        db.update_autonomy_run(safe_run["id"], task_ids=[safe_task["id"]])
        verification_run = db.create_autonomy_run(self.project["id"], "verify", 1)
        verification_task = self._task(status="running", run_id=verification_run["id"])
        db.update_task(verification_task["id"], heartbeat_at="2020-01-01T00:00:00+00:00", lease_expires_at="2020-01-01T00:00:00+00:00", recovery_state="active")
        db.update_autonomy_run(verification_run["id"], task_ids=[verification_task["id"]], status="running")
        reports = recover_incomplete_runs(stale_after_seconds=30)
        by_run = {item["run_id"]: item for item in reports}
        self.assertEqual(by_run[safe_run["id"]]["tasks"][0]["classification"], "safe_to_resume")
        self.assertEqual(by_run[verification_run["id"]]["tasks"][0]["classification"], "needs_verification")
        self.assertEqual(db.get_task(safe_task["id"])["status"], "queued")
        self.assertEqual(db.get_task(verification_task["id"])["status"], "needs_verification")
        self.assertEqual(db.get_autonomy_run(verification_run["id"])["status"], "recovery_required")

    def test_resume_requires_verification_and_is_idempotent(self) -> None:
        run = db.create_autonomy_run(self.project["id"], "resume", 1)
        task = self._task(status="needs_verification", run_id=run["id"])
        db.update_autonomy_run(run["id"], task_ids=[task["id"]], status="recovery_required")
        with self.assertRaises(Exception):
            resume_run(run["id"])
        resumed = resume_run(run["id"], verify=True)
        repeated = resume_run(run["id"], verify=True)
        self.assertEqual(resumed["id"], repeated["id"])
        self.assertEqual(repeated["status"], "queued")
        with db.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM recovery_events WHERE event_type = 'run_resumed' AND run_id = ?", (run["id"],)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_completed_task_is_not_reexecuted_by_recovery(self) -> None:
        task = self._task(status="completed")
        self.assertEqual(classify_task(db.get_task(task["id"])), "completed")
        self.assertEqual(get_recovery_status()["runs"], [])

    def test_recovery_persists_provider_failure_evidence(self) -> None:
        run = db.create_autonomy_run(self.project["id"], "provider", 1)
        task = self._task(run_id=run["id"])
        pause_task_for_dependency(task["id"], "provider", "rate limit", run_id=run["id"])
        with db.connect() as connection:
            row = connection.execute("SELECT dependency, fallback_provider FROM provider_failures WHERE task_id = ?", (task["id"],)).fetchone()
        self.assertEqual(tuple(row), ("provider", None))


if __name__ == "__main__":
    unittest.main()
