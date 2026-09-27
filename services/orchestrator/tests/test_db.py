from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "orchestrator.db"

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_initialize_is_idempotent_and_creates_all_core_tables(self) -> None:
        db.initialize_database(self.database_path)
        db.initialize_database(self.database_path)

        with db.connect(self.database_path) as connection:
            version = connection.execute(
                "SELECT version FROM schema_version WHERE id = 1"
            ).fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            task_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(agent_tasks)")
            }
            project_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(projects)")
            }

        self.assertEqual(version, db.SCHEMA_VERSION)
        self.assertTrue(
            {
                "projects", "agent_tasks", "agent_memories", "autonomy_runs",
                "subagent_handoffs", "agent_profiles", "project_team_members",
            } <= tables
        )
        self.assertIn("mode", task_columns)
        self.assertTrue(
            {"project_manager_id", "engineering_manager_id", "departments_json",
             "phase", "priority", "team_state"} <= project_columns
        )

    def test_legacy_database_upgrade_preserves_rows_and_adds_mode(self) -> None:
        project_id = "legacy-project"
        run_id = "legacy-run"
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    workspace TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE agent_tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT NOT NULL DEFAULT '[]',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    results_json TEXT NOT NULL DEFAULT '[]',
                    approved_steps_json TEXT NOT NULL DEFAULT '[]',
                    pending_json TEXT,
                    final_output TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE agent_memories (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT,
                    kind TEXT NOT NULL, summary TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}', confidence REAL NOT NULL DEFAULT 0.5,
                    created_at TEXT NOT NULL, last_used_at TEXT,
                    use_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE autonomy_runs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, goal TEXT NOT NULL,
                    requested_cycles INTEGER NOT NULL, completed_cycles INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL, task_ids_json TEXT NOT NULL DEFAULT '[]',
                    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE subagent_handoffs (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, project_id TEXT NOT NULL,
                    task_id TEXT, role TEXT NOT NULL, section TEXT NOT NULL,
                    schema_version TEXT NOT NULL DEFAULT '1.0', status TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '', evidence_json TEXT NOT NULL DEFAULT '[]',
                    changed_files_json TEXT NOT NULL DEFAULT '[]', validations_json TEXT NOT NULL DEFAULT '[]',
                    blockers_json TEXT NOT NULL DEFAULT '[]', next_action TEXT,
                    confidence REAL NOT NULL DEFAULT 0, previous_handoff_ids_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO projects VALUES (?, ?, ?, ?, ?)",
                (project_id, "Legacy", "legacy", "2026-01-01", "2026-01-01"),
            )
            connection.execute(
                "INSERT INTO autonomy_runs(id, project_id, goal, requested_cycles, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, project_id, "preserve me", 2, "queued", "2026-01-01", "2026-01-01"),
            )

        connection.close()

        db.initialize_database(self.database_path)

        with db.connect(self.database_path) as connection:
            project = connection.execute(
                "SELECT name FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            run = connection.execute(
                "SELECT goal FROM autonomy_runs WHERE id = ?", (run_id,)
            ).fetchone()
            task_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(agent_tasks)")
            }

        self.assertEqual(project[0], "Legacy")
        self.assertEqual(run[0], "preserve me")
        self.assertIn("mode", task_columns)

    def test_autonomy_run_persists_and_isolated_database_paths_do_not_leak(self) -> None:
        with patch.object(db, "DATABASE_PATH", self.database_path):
            db.initialize_database()
            project = db.create_project("Project", "workspace")
            created = db.create_autonomy_run(project["id"], "ship", 3)
            updated = db.update_autonomy_run(
                created["id"],
                status="completed",
                completed_cycles=3,
                task_ids=["task-1"],
            )
            self.assertEqual(db.get_autonomy_run(created["id"]), updated)
            self.assertEqual(updated["task_ids"], ["task-1"])

        other_path = Path(self._temporary_directory.name) / "other.db"
        db.initialize_database(other_path)
        with db.connect(other_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM autonomy_runs").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
