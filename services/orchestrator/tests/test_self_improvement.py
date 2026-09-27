from __future__ import annotations
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import db
from app.autonomy import _push_verified_checkpoint
from app.db import create_project, create_task, initialize_database, update_task
from app.self_improvement import SelfImprovementEngine

class ControlledSelfImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "orchestrator.db"
        self.old_database_path = db.DATABASE_PATH
        db.DATABASE_PATH = self.database_path
        initialize_database(self.database_path)
        self.project = create_project("Phase 4", f"phase4-{Path(self.temp.name).name}")
    def tearDown(self):
        db.DATABASE_PATH = self.old_database_path
        self.temp.cleanup()
    def candidate(self, engine):
        rows = engine.propose(self.project["id"], [{
            "kind": "test_failure", "problem": "SQLite table missing", "severity": "high",
            "module": "services/orchestrator/app/db.py",
            "evidence": [{"source": "pytest", "message": "api_key=secret-value"}],
        }])
        self.assertTrue(rows)
        self.assertNotIn("secret-value", str(rows[0]["evidence"]))
        self.assertTrue(rows[0]["failure_signature"])
        return rows[0]
    def test_observation_prioritization_and_retry_avoidance(self):
        task = create_task(self.project["id"], "repeated failure", mode="autonomous")
        update_task(task["id"], status="failed", error="SQLite table missing")
        engine = SelfImprovementEngine(self.database_path)
        rows = engine.observe_and_propose(self.project["id"])
        self.assertTrue(rows)
        self.assertEqual(rows[0]["severity"], "high")
        first = engine.prioritize(self.project["id"])[0]
        cycle = engine.start_cycle(first["id"], project_id=self.project["id"])
        self.assertEqual(cycle["stage"], "planned")
        self.assertEqual(engine.start_cycle(first["id"], project_id=self.project["id"])["id"], cycle["id"])
        self.assertTrue(engine.enforce_limits(changes=0, files_changed=0, retries=0, elapsed_seconds=0)["allowed"])
    def test_checkpoint_and_rejection_persist_assessment(self):
        repo = Path(self.temp.name) / "repo"
        repo.mkdir()
        for command in (["git", "init", "-q"], ["git", "config", "user.email", "test@example.invalid"], ["git", "config", "user.name", "Phase4 Test"]):
            subprocess.run(command, cwd=repo, check=True, capture_output=True)
        (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "module.py"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo, check=True, capture_output=True)
        engine = SelfImprovementEngine(self.database_path, repo_root=repo)
        candidate = self.candidate(engine)
        cycle = engine.start_cycle(candidate["id"], project_id=self.project["id"], expected_files=["module.py"])
        checkpoint = engine.checkpoint(cycle["id"], repo_root=repo)
        self.assertEqual(checkpoint["stage"], "checkpointed")
        engine.record_tests(cycle["id"], phase="after", results={"summary": "failed"}, passed=False)
        result = engine.review(cycle["id"], tests_passed=False, review_accepted=False, acceptance_met=False, review_summary="Regression remains.")
        self.assertEqual(result["stage"], "rejected")
        self.assertTrue(result["lesson_memory_id"])
        self.assertEqual(result["assessment"]["action_taken"], "improvement rejected")
    def test_acceptance_promotes_lesson_and_resume(self):
        engine = SelfImprovementEngine(self.database_path)
        candidate = self.candidate(engine)
        cycle = engine.start_cycle(candidate["id"], project_id=self.project["id"])
        self.assertEqual(engine.interrupt(cycle["id"], "worker stopped")["stage"], "interrupted")
        self.assertEqual(engine.resume(cycle["id"])["stage"], "planned")
        engine.record_tests(cycle["id"], phase="before", results={"passed": True}, passed=True)
        engine.record_tests(cycle["id"], phase="after", results={"passed": True}, passed=True)
        result = engine.review(cycle["id"], tests_passed=True, review_accepted=True, acceptance_met=True, confidence=0.9)
        self.assertEqual(result["stage"], "accepted")
        self.assertTrue(result["lesson_memory_id"])
        with db.connect(self.database_path) as connection:
            row = connection.execute("SELECT lifecycle FROM experience_memories WHERE id = ?", (result["lesson_memory_id"],)).fetchone()
        self.assertEqual(row["lifecycle"], "trusted")
    def test_limits_and_remote_push_safety(self):
        with patch("app.config.settings.autonomous_auto_push", True):
            result = _push_verified_checkpoint({".git/config"})
        self.assertFalse(result["pushed"])
        self.assertIn("disabled", result["reason"])
        engine = SelfImprovementEngine(self.database_path)
        self.assertFalse(engine.enforce_limits(changes=2, files_changed=0, retries=0, elapsed_seconds=0)["allowed"])
        self.assertFalse(engine.enforce_limits(changes=0, files_changed=0, retries=0, elapsed_seconds=engine.max_runtime + 1)["allowed"])
        candidate = self.candidate(engine)
        with db.connect(self.database_path) as connection:
            connection.execute("UPDATE improvement_candidates SET attempts=? WHERE id=?", (engine.max_retries + 1, candidate["id"]))
        with self.assertRaises(ValueError):
            engine.start_cycle(candidate["id"], project_id=self.project["id"])

if __name__ == "__main__":
    unittest.main()
