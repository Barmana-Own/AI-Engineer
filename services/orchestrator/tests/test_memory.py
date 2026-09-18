from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import create_project, initialize_database
from app.memory import MemoryLifecycle, MemoryStore, MemoryType, contains_secret_like


class EngineeringMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "memory.db"
        initialize_database(self.db)
        project = create_project("memory-test", self.temp.name, database_path=self.db)
        self.project_id = str(project["id"])
        self.store = MemoryStore(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_candidate_memory_requires_evidence_before_retrieval(self) -> None:
        memory = self.store.create(
            project_id=self.project_id,
            memory_type=MemoryType.LESSON,
            role="backend",
            task_type="api",
            summary="Use contract tests for API changes",
            content={"files": ["app/api.py"]},
        )
        self.assertEqual(memory["lifecycle"], MemoryLifecycle.CANDIDATE.value)
        self.assertEqual(
            self.store.retrieve(
                project_id=self.project_id,
                query="contract tests",
                role="backend",
            ),
            [],
        )
        validated = self.store.promote(
            memory["id"],
            evidence=[{"type": "test", "command": "pytest", "passed": True}],
            target=MemoryLifecycle.VALIDATED,
        )
        self.assertEqual(validated["lifecycle"], MemoryLifecycle.VALIDATED.value)
        self.assertEqual(
            len(
                self.store.retrieve(
                    project_id=self.project_id,
                    query="contract tests",
                    role="backend",
                )
            ),
            1,
        )

    def test_outcomes_update_confidence_and_promote_repeated_success(self) -> None:
        memory = self.store.create(
            project_id=self.project_id,
            memory_type="lesson",
            role="tester",
            task_type="validation",
            summary="Run the focused regression suite before release",
        )
        initial_confidence = float(memory["confidence"])
        self.store.record_outcome(
            memory["id"],
            outcome="success",
            task_success=True,
            tests_passed=True,
            review_accepted=True,
        )
        validated = self.store.get(memory["id"])
        self.assertEqual(validated["lifecycle"], MemoryLifecycle.VALIDATED.value)
        self.assertGreater(float(validated["confidence"]), initial_confidence)
        trusted = self.store.record_outcome(
            memory["id"],
            outcome="success",
            task_success=True,
            tests_passed=True,
            review_accepted=True,
        )
        self.assertEqual(trusted["lifecycle"], MemoryLifecycle.TRUSTED.value)
        self.assertEqual(trusted["successful_uses"], 2)

    def test_irrelevant_and_superseded_memories_are_not_prioritized(self) -> None:
        relevant = self.store.create(
            project_id=self.project_id,
            memory_type="project",
            role="backend",
            task_type="migration",
            summary="SQLite migrations must be idempotent",
        )
        irrelevant = self.store.create(
            project_id=self.project_id,
            memory_type="project",
            role="frontend",
            task_type="styling",
            summary="Use a restrained spacing scale for forms",
        )
        for item in (relevant, irrelevant):
            self.store.promote(
                item["id"],
                evidence=[{"type": "inspection", "summary": "reviewed project convention"}],
            )
        found = self.store.retrieve(
            project_id=self.project_id,
            query="SQLite migrations",
            role="backend",
            task_type="migration",
        )
        self.assertEqual([item["id"] for item in found], [relevant["id"]])
        replacement = self.store.create(
            project_id=self.project_id,
            memory_type="project",
            role="backend",
            task_type="migration",
            summary="SQLite migrations use explicit schema versions",
        )
        self.store.promote(
            replacement["id"],
            evidence=[{"type": "review", "summary": "accepted replacement"}],
        )
        self.store.supersede(relevant["id"], replacement["id"])
        after = self.store.retrieve(
            project_id=self.project_id,
            query="SQLite migrations",
            role="backend",
            task_type="migration",
        )
        self.assertNotIn(relevant["id"], [item["id"] for item in after])
        self.assertIn(replacement["id"], [item["id"] for item in after])

    def test_failure_patterns_recur_and_expose_successful_fix(self) -> None:
        first = self.store.capture_failure(
            project_id=self.project_id,
            role="tester",
            title="SQLite table missing",
            reason="SQLite table missing because migration was not applied",
            successful_fix="Run the deterministic migration before tests",
        )
        second = self.store.capture_failure(
            project_id=self.project_id,
            role="tester",
            title="SQLite table missing again",
            reason="SQLite table missing because migration was not applied",
            successful_fix="Run the deterministic migration before tests",
        )
        self.assertEqual(first["lifecycle"], MemoryLifecycle.CANDIDATE.value)
        patterns = self.store.failure_patterns(
            project_id=self.project_id,
            query="sqlite migration",
        )
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["occurrences"], 2)
        self.assertEqual(patterns[0]["successful_fix"], "Run the deterministic migration before tests")
        self.assertEqual(second["memory_type"], MemoryType.FAILURE.value)

    def test_memory_sanitizes_secret_like_content(self) -> None:
        memory = self.store.create(
            project_id=self.project_id,
            memory_type=MemoryType.EPISODIC,
            summary="Observed api_key=super-secret-value during a run",
            content={"token": "Bearer abcdefghijklmnop", "note": "safe context"},
            evidence=[{"type": "log", "summary": "password=hunter2"}],
        )
        self.assertNotIn("super-secret-value", memory["summary"])
        self.assertNotIn("abcdefghijklmnop", str(memory["content"]))
        self.assertNotIn("hunter2", str(memory["evidence"]))
        self.assertTrue(memory["content"].get("redacted"))
        self.assertFalse(contains_secret_like(memory["content"]))
        self.assertFalse(contains_secret_like(memory["evidence"]))

    def test_task_experience_updates_agent_performance(self) -> None:
        memory = self.store.extract_task_experience(
            project_id=self.project_id,
            run_id=None,
            task_id=None,
            role="backend",
            task_type="api",
            summary="Implemented endpoint with focused tests",
            evidence=[{"type": "test", "command": "pytest", "passed": True}],
            changed_files=["app/api.py"],
            validations=["pytest tests/test_api.py"],
            success=True,
            tests_passed=True,
        )
        rows = self.store.performance(role="backend", domain="api")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tasks_attempted"], 1)
        self.assertEqual(rows[0]["tasks_completed"], 1)
        self.assertEqual(memory["lifecycle"], MemoryLifecycle.CANDIDATE.value)



    def test_raw_memories_cannot_be_created_as_trusted(self) -> None:
        with self.assertRaises(ValueError):
            self.store.create(
                project_id=self.project_id,
                memory_type="lesson",
                summary="Direct trusted memory is forbidden",
                lifecycle=MemoryLifecycle.TRUSTED,
                evidence=[{"type": "test", "command": "pytest"}],
            )
        with self.assertRaises(ValueError):
            self.store.create(
                project_id=self.project_id,
                memory_type="lesson",
                summary="Validated memory needs evidence",
                lifecycle=MemoryLifecycle.VALIDATED,
            )
        validated = self.store.create(
            project_id=self.project_id,
            memory_type="lesson",
            summary="Validated memory has evidence",
            lifecycle=MemoryLifecycle.VALIDATED,
            evidence=[{"type": "review", "summary": "accepted"}],
        )
        self.assertEqual(validated["lifecycle"], MemoryLifecycle.VALIDATED.value)

if __name__ == "__main__":
    unittest.main()
