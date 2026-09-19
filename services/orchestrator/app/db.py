from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[3] / "data" / "orchestrator" / "orchestrator.db"
DATABASE_PATH = Path(
    os.getenv("ORCHESTRATOR_DB_PATH", str(_DEFAULT_DATABASE_PATH))
).expanduser()
MEMORY_INSTRUCTION_LIMIT = 4_000
MEMORY_ITEM_LIMIT = 1_000
MEMORY_JSON_MAX_BYTES = 4 * 1024 * 1024


def _bounded_memory_values(
    values: list[str],
    *,
    limit: int,
    item_limit: int = MEMORY_ITEM_LIMIT,
) -> list[str]:
    """Keep episodic evidence unique and bounded before serializing it."""
    bounded: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if len(text) > item_limit:
            text = text[:item_limit] + "..."
        if text not in bounded:
            bounded.append(text)
    return bounded[-max(int(limit), 1):]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA_VERSION = 11
_SCHEMA_VERSION_TABLE = "schema_version"


class _ManagedConnection(sqlite3.Connection):
    """Commit/rollback and close when used as a context manager.

    sqlite3.Connection.__exit__ does not close the handle, which leaves
    temporary database files locked on Windows and makes test isolation flaky.
    """

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _database_path(value: str | os.PathLike[str] | None = None) -> Path:
    """Resolve a database path without changing the public DATABASE_PATH hook."""
    return Path(value if value is not None else DATABASE_PATH).expanduser()


def connect(
    database_path: str | os.PathLike[str] | None = None,
) -> sqlite3.Connection:
    """Open a configured SQLite connection.

    ``database_path`` is optional so production callers keep using
    ``DATABASE_PATH`` while tests can create isolated databases without
    mutating process-wide configuration.
    """
    path = _database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30, factory=_ManagedConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _migration_1(database: sqlite3.Connection) -> None:
    """Create the original durable schema."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            workspace TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_tasks (
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
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_id TEXT,
            kind TEXT NOT NULL,
            summary TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}',
            confidence REAL NOT NULL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            use_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS autonomy_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            goal TEXT NOT NULL,
            requested_cycles INTEGER NOT NULL,
            completed_cycles INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            task_ids_json TEXT NOT NULL DEFAULT '[]',
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS subagent_handoffs (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            task_id TEXT,
            role TEXT NOT NULL,
            section TEXT NOT NULL,
            schema_version TEXT NOT NULL DEFAULT '1.0',
            status TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            changed_files_json TEXT NOT NULL DEFAULT '[]',
            validations_json TEXT NOT NULL DEFAULT '[]',
            blockers_json TEXT NOT NULL DEFAULT '[]',
            next_action TEXT,
            confidence REAL NOT NULL DEFAULT 0,
            previous_handoff_ids_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        """
    )


def _migration_2(database: sqlite3.Connection) -> None:
    """Add task execution mode and indexes introduced after the initial schema."""
    task_columns = {
        str(row[1])
        for row in database.execute("PRAGMA table_info(agent_tasks)").fetchall()
    }
    if "mode" not in task_columns:
        database.execute(
            "ALTER TABLE agent_tasks ADD COLUMN mode TEXT NOT NULL DEFAULT 'interactive'"
        )
    database.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_tasks_project
            ON agent_tasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_agent_tasks_status
            ON agent_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_agent_memories_project
            ON agent_memories(project_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_subagent_handoffs_run
            ON subagent_handoffs(run_id, created_at ASC);
        CREATE INDEX IF NOT EXISTS idx_subagent_handoffs_project
            ON subagent_handoffs(project_id, updated_at DESC);
        """
    )



def _migration_3(database: sqlite3.Connection) -> None:
    """Create additive durable coordination tables for the multi-agent engine."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS coordination_tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            run_id TEXT,
            parent_task_id TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            role TEXT NOT NULL,
            assigned_agent TEXT,
            state TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 50,
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            blocked_by_json TEXT NOT NULL DEFAULT '[]',
            inputs_json TEXT NOT NULL DEFAULT '{}',
            expected_outputs_json TEXT NOT NULL DEFAULT '[]',
            acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 2,
            failure_reason TEXT,
            scope_json TEXT NOT NULL DEFAULT '[]',
            writer INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(parent_task_id) REFERENCES coordination_tasks(id)
        );
        CREATE TABLE IF NOT EXISTS coordination_task_dependencies (
            task_id TEXT NOT NULL,
            depends_on_task_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(task_id, depends_on_task_id),
            FOREIGN KEY(task_id) REFERENCES coordination_tasks(id) ON DELETE CASCADE,
            FOREIGN KEY(depends_on_task_id) REFERENCES coordination_tasks(id) ON DELETE CASCADE,
            CHECK(task_id <> depends_on_task_id)
        );
        CREATE TABLE IF NOT EXISTS agent_messages (
            message_id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            task_id TEXT,
            sender_role TEXT NOT NULL,
            recipient_role TEXT,
            message_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            references_json TEXT NOT NULL DEFAULT '[]',
            discussion_round INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(task_id) REFERENCES coordination_tasks(id)
        );
        CREATE TABLE IF NOT EXISTS coordination_handoffs (
            handoff_id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            task_id TEXT,
            sender_role TEXT NOT NULL,
            recipient_role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'submitted',
            summary TEXT NOT NULL,
            completed_json TEXT NOT NULL DEFAULT '[]',
            artifacts_json TEXT NOT NULL DEFAULT '[]',
            changed_files_json TEXT NOT NULL DEFAULT '[]',
            decisions_json TEXT NOT NULL DEFAULT '[]',
            risks_json TEXT NOT NULL DEFAULT '[]',
            remaining_work_json TEXT NOT NULL DEFAULT '[]',
            verification_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(task_id) REFERENCES coordination_tasks(id)
        );
        CREATE TABLE IF NOT EXISTS coordination_locks (
            resource TEXT PRIMARY KEY,
            owner_task_id TEXT NOT NULL,
            owner_role TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'write',
            acquired_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY(owner_task_id) REFERENCES coordination_tasks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_coord_tasks_run_state ON coordination_tasks(run_id, state, priority DESC);
        CREATE INDEX IF NOT EXISTS idx_coord_tasks_project ON coordination_tasks(project_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_coord_messages_scope ON agent_messages(run_id, project_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_coord_handoffs_scope ON coordination_handoffs(run_id, project_id, updated_at);
        CREATE INDEX IF NOT EXISTS idx_coord_deps_dependency ON coordination_task_dependencies(depends_on_task_id);
        """
    )


def _migration_4(database: sqlite3.Connection) -> None:
    """Create durable engineering experience and measurable outcome tables."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS experience_memories (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            task_id TEXT,
            memory_type TEXT NOT NULL,
            lifecycle TEXT NOT NULL DEFAULT 'candidate',
            role TEXT,
            task_type TEXT,
            summary TEXT NOT NULL,
            content_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 0.5,
            usefulness REAL NOT NULL DEFAULT 0.5,
            use_count INTEGER NOT NULL DEFAULT 0,
            successful_uses INTEGER NOT NULL DEFAULT 0,
            failed_uses INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'system',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_used_at TEXT,
            superseded_by TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(task_id) REFERENCES coordination_tasks(id),
            FOREIGN KEY(superseded_by) REFERENCES experience_memories(id),
            CHECK(memory_type IN ('working','episodic','project','lesson','failure')),
            CHECK(lifecycle IN ('candidate','validated','trusted','superseded','rejected')),
            CHECK(confidence >= 0 AND confidence <= 1),
            CHECK(usefulness >= 0 AND usefulness <= 1)
        );
        CREATE INDEX IF NOT EXISTS idx_experience_scope
            ON experience_memories(project_id, lifecycle, memory_type, updated_at);
        CREATE INDEX IF NOT EXISTS idx_experience_role
            ON experience_memories(project_id, role, task_type, lifecycle);
        CREATE TABLE IF NOT EXISTS experience_outcomes (
            id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            project_id TEXT,
            run_id TEXT,
            task_id TEXT,
            outcome TEXT NOT NULL,
            task_success INTEGER,
            tests_passed INTEGER,
            review_accepted INTEGER,
            rework_required INTEGER NOT NULL DEFAULT 0,
            notes_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(memory_id) REFERENCES experience_memories(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(task_id) REFERENCES coordination_tasks(id),
            CHECK(outcome IN ('success','failure','review_rejected','test_failed','superseded'))
        );
        CREATE INDEX IF NOT EXISTS idx_experience_outcomes_memory
            ON experience_outcomes(memory_id, created_at);
        CREATE TABLE IF NOT EXISTS failure_patterns (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            signature TEXT NOT NULL,
            title TEXT NOT NULL,
            root_cause TEXT NOT NULL,
            successful_fix TEXT,
            linked_memory_id TEXT,
            occurrences INTEGER NOT NULL DEFAULT 1,
            resolved_count INTEGER NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0.35,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(linked_memory_id) REFERENCES experience_memories(id),
            CHECK(confidence >= 0 AND confidence <= 1),
            UNIQUE(project_id, signature)
        );
        CREATE INDEX IF NOT EXISTS idx_failure_patterns_scope
            ON failure_patterns(project_id, updated_at, occurrences DESC);
        CREATE TABLE IF NOT EXISTS agent_performance (
            role TEXT NOT NULL,
            model_profile TEXT NOT NULL,
            domain TEXT NOT NULL DEFAULT '',
            tasks_attempted INTEGER NOT NULL DEFAULT 0,
            tasks_completed INTEGER NOT NULL DEFAULT 0,
            review_rejections INTEGER NOT NULL DEFAULT 0,
            test_failures INTEGER NOT NULL DEFAULT 0,
            total_retries INTEGER NOT NULL DEFAULT 0,
            total_duration_seconds REAL NOT NULL DEFAULT 0,
            successful_domains_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            PRIMARY KEY(role, model_profile, domain)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_performance_role
            ON agent_performance(role, model_profile, tasks_completed DESC);
        """
    )

def _migration_5(database: sqlite3.Connection) -> None:
    """Create persisted, resumable controlled self-improvement state."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS improvement_candidates (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            run_id TEXT,
            problem TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            severity TEXT NOT NULL DEFAULT 'medium',
            affected_modules_json TEXT NOT NULL DEFAULT '[]',
            proposed_outcome TEXT NOT NULL,
            estimated_risk TEXT NOT NULL DEFAULT 'medium',
            expected_verification_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'candidate',
            priority_score REAL NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TEXT,
            next_attempt_after TEXT,
            failure_signature TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_improvement_candidates_priority
            ON improvement_candidates(project_id, status, priority_score DESC, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_improvement_candidates_signature
            ON improvement_candidates(project_id, failure_signature);
        CREATE TABLE IF NOT EXISTS improvement_cycles (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            run_id TEXT,
            stage TEXT NOT NULL DEFAULT 'planned',
            baseline_commit TEXT,
            baseline_status TEXT NOT NULL DEFAULT '',
            checkpoint_ref TEXT,
            expected_files_json TEXT NOT NULL DEFAULT '[]',
            expected_tests_json TEXT NOT NULL DEFAULT '[]',
            tests_before_json TEXT NOT NULL DEFAULT '{}',
            tests_after_json TEXT NOT NULL DEFAULT '{}',
            review_result_json TEXT NOT NULL DEFAULT '{}',
            regressions_json TEXT NOT NULL DEFAULT '[]',
            assessment_json TEXT NOT NULL DEFAULT '{}',
            lesson_memory_id TEXT,
            confidence REAL NOT NULL DEFAULT 0,
            follow_up_tasks_json TEXT NOT NULL DEFAULT '[]',
            error TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES improvement_candidates(id),
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id),
            FOREIGN KEY(lesson_memory_id) REFERENCES experience_memories(id)
        );
        CREATE INDEX IF NOT EXISTS idx_improvement_cycles_candidate
            ON improvement_cycles(candidate_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_improvement_cycles_project
            ON improvement_cycles(project_id, stage, updated_at DESC);
        """
    )


def _migration_6(database: sqlite3.Connection) -> None:
    """Add durable execution leases, recovery metadata, and dependency events."""
    def add_column(table: str, column: str, definition: str) -> None:
        columns = {
            str(row[1])
            for row in database.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            database.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    task_columns = {
        "run_id": "TEXT",
        "lease_owner": "TEXT",
        "lease_token": "TEXT",
        "lease_expires_at": "TEXT",
        "heartbeat_at": "TEXT",
        "attempt_count": "INTEGER NOT NULL DEFAULT 0",
        "recovery_state": "TEXT NOT NULL DEFAULT 'new'",
        "failure_kind": "TEXT",
        "provider": "TEXT",
        "fallback_provider": "TEXT",
        "retry_after": "TEXT",
        "last_checkpoint_ref": "TEXT",
    }
    for column, definition in task_columns.items():
        add_column("agent_tasks", column, definition)

    run_columns = {
        "current_stage": "TEXT NOT NULL DEFAULT 'queued'",
        "recovery_state": "TEXT NOT NULL DEFAULT 'new'",
        "lease_owner": "TEXT",
        "lease_token": "TEXT",
        "lease_expires_at": "TEXT",
        "heartbeat_at": "TEXT",
        "retry_count": "INTEGER NOT NULL DEFAULT 0",
        "failure_kind": "TEXT",
        "provider": "TEXT",
        "fallback_provider": "TEXT",
        "checkpoint_ref": "TEXT",
        "pending_approval_json": "TEXT",
        "last_recovery_at": "TEXT",
    }
    for column, definition in run_columns.items():
        add_column("autonomy_runs", column, definition)

    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS execution_leases (
            resource TEXT PRIMARY KEY,
            task_id TEXT UNIQUE,
            run_id TEXT,
            owner_id TEXT NOT NULL,
            lease_token TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL DEFAULT 'active',
            acquired_at TEXT NOT NULL,
            heartbeat_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            released_at TEXT,
            last_error TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_execution_leases_expiry
            ON execution_leases(state, expires_at);
        CREATE INDEX IF NOT EXISTS idx_execution_leases_run
            ON execution_leases(run_id, state);

        CREATE TABLE IF NOT EXISTS recovery_events (
            id TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            run_id TEXT,
            task_id TEXT,
            event_type TEXT NOT NULL,
            from_state TEXT,
            to_state TEXT,
            classification TEXT,
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id) ON DELETE CASCADE,
            FOREIGN KEY(task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_recovery_events_scope
            ON recovery_events(run_id, task_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS provider_failures (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            task_id TEXT,
            dependency TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            error_code TEXT,
            error_detail TEXT NOT NULL DEFAULT '',
            fallback_provider TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY(run_id) REFERENCES autonomy_runs(id) ON DELETE CASCADE,
            FOREIGN KEY(task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_provider_failures_scope
            ON provider_failures(run_id, task_id, created_at DESC);
        """
    )


def _migration_7(database: sqlite3.Connection) -> None:
    """Add the persistent organizational layer without replacing coordination."""
    def add_column(table: str, column: str, definition: str) -> None:
        columns = {
            str(row[1])
            for row in database.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            database.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    project_columns = {
        "project_manager_id": "TEXT",
        "engineering_manager_id": "TEXT",
        "departments_json": "TEXT NOT NULL DEFAULT '[]'",
        "phase": "TEXT NOT NULL DEFAULT 'initiating'",
        "priority": "INTEGER NOT NULL DEFAULT 50",
        "team_state": "TEXT NOT NULL DEFAULT 'forming'",
    }
    for column, definition in project_columns.items():
        add_column("projects", column, definition)

    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_profiles (
            agent_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            display_name TEXT NOT NULL,
            department TEXT NOT NULL,
            capabilities_json TEXT NOT NULL DEFAULT '[]',
            specializations_json TEXT NOT NULL DEFAULT '[]',
            allowed_tools_json TEXT NOT NULL DEFAULT '[]',
            write_permission TEXT NOT NULL DEFAULT 'read_only',
            model_profile TEXT NOT NULL DEFAULT 'balanced',
            status TEXT NOT NULL DEFAULT 'offline',
            active_project TEXT,
            current_tasks_json TEXT NOT NULL DEFAULT '[]',
            experience_summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(active_project) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_profiles_role
            ON agent_profiles(role);
        CREATE INDEX IF NOT EXISTS idx_agent_profiles_department
            ON agent_profiles(department);
        CREATE INDEX IF NOT EXISTS idx_agent_profiles_status
            ON agent_profiles(status);

        CREATE TABLE IF NOT EXISTS project_team_members (
            project_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            is_lead INTEGER NOT NULL DEFAULT 0,
            assigned_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(project_id, agent_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(agent_id) REFERENCES agent_profiles(agent_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_project_team_project
            ON project_team_members(project_id, role);
        CREATE INDEX IF NOT EXISTS idx_project_team_agent
            ON project_team_members(agent_id, status);
        """
    )


def _migration_8(database: sqlite3.Connection) -> None:
    """Add persisted collaboration scopes, decisions, meetings and work requests."""
    def add_column(table: str, column: str, definition: str) -> None:
        columns = {
            str(row[1])
            for row in database.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            database.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    for column, definition in {
        "conversation_id": "TEXT",
        "audience_type": "TEXT NOT NULL DEFAULT 'direct'",
        "audience_id": "TEXT",
        "participant_roles_json": "TEXT NOT NULL DEFAULT '[]'",
        "topic": "TEXT NOT NULL DEFAULT ''",
    }.items():
        add_column("agent_messages", column, definition)

    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS coordination_conversations (
            conversation_id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            task_id TEXT,
            conversation_type TEXT NOT NULL DEFAULT 'direct',
            subject TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT '',
            participants_json TEXT NOT NULL DEFAULT '[]',
            department TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_coord_conversations_project
            ON coordination_conversations(project_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_coord_conversations_scope
            ON coordination_conversations(run_id, task_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_coord_conversations_type
            ON coordination_conversations(conversation_type, department);

        CREATE INDEX IF NOT EXISTS idx_coord_messages_conversation
            ON agent_messages(conversation_id, created_at ASC);
        CREATE INDEX IF NOT EXISTS idx_coord_messages_audience
            ON agent_messages(audience_type, audience_id, created_at ASC);

        CREATE TABLE IF NOT EXISTS coordination_decisions (
            decision_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            run_id TEXT,
            meeting_id TEXT,
            title TEXT NOT NULL,
            context TEXT NOT NULL,
            options_json TEXT NOT NULL DEFAULT '[]',
            arguments_json TEXT NOT NULL DEFAULT '[]',
            decision TEXT NOT NULL,
            decision_maker TEXT NOT NULL,
            supporting_evidence_json TEXT NOT NULL DEFAULT '[]',
            affected_tasks_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            superseded_by TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_coord_decisions_project
            ON coordination_decisions(project_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_coord_decisions_meeting
            ON coordination_decisions(meeting_id, created_at ASC);

        CREATE TABLE IF NOT EXISTS coordination_meetings (
            meeting_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            run_id TEXT,
            meeting_type TEXT NOT NULL,
            objective TEXT NOT NULL,
            participants_json TEXT NOT NULL DEFAULT '[]',
            agenda_json TEXT NOT NULL DEFAULT '[]',
            message_ids_json TEXT NOT NULL DEFAULT '[]',
            decision_ids_json TEXT NOT NULL DEFAULT '[]',
            action_items_json TEXT NOT NULL DEFAULT '[]',
            unresolved_questions_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'scheduled',
            started_at TEXT,
            ended_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_coord_meetings_project
            ON coordination_meetings(project_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_coord_meetings_status
            ON coordination_meetings(status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS agent_work_requests (
            request_id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            project_id TEXT NOT NULL,
            run_id TEXT,
            task_id TEXT,
            request_type TEXT NOT NULL,
            description TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'open',
            response TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_agent_requests_project
            ON agent_work_requests(project_id, status, priority DESC);
        CREATE INDEX IF NOT EXISTS idx_agent_requests_recipient
            ON agent_work_requests(recipient, status, updated_at ASC);
        """
    )


def _migration_9(database: sqlite3.Connection) -> None:
    """Add project management, lifecycle, queues, gates and risk state."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS project_lifecycle_events (
            event_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            from_phase TEXT,
            to_phase TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_project_lifecycle_events_project
            ON project_lifecycle_events(project_id, created_at ASC);
        CREATE TABLE IF NOT EXISTS project_milestones (
            milestone_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'planned',
            due_at TEXT,
            deliverables_json TEXT NOT NULL DEFAULT '[]',
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_project_milestones_project
            ON project_milestones(project_id, state, due_at);
        CREATE TABLE IF NOT EXISTS project_risks (
            risk_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            mitigation TEXT NOT NULL DEFAULT '',
            owner TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_project_risks_project
            ON project_risks(project_id, status, severity);
        CREATE TABLE IF NOT EXISTS project_quality_gates (
            gate_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            gate_name TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, gate_name)
        );
        CREATE INDEX IF NOT EXISTS idx_project_gates_project
            ON project_quality_gates(project_id, status);
        CREATE TABLE IF NOT EXISTS agent_work_queue (
            queue_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            task_id TEXT,
            item_type TEXT NOT NULL,
            item_ref TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'queued',
            blocked_by_json TEXT NOT NULL DEFAULT '[]',
            available_at TEXT,
            claimed_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(agent_id, item_type, item_ref)
        );
        CREATE INDEX IF NOT EXISTS idx_work_queue_agent
            ON agent_work_queue(agent_id, status, priority DESC, created_at ASC);
        CREATE INDEX IF NOT EXISTS idx_work_queue_project
            ON agent_work_queue(project_id, status, priority DESC);
        """
    )


def _migration_10(database: sqlite3.Connection) -> None:
    """Add incident response, owner control and external intake state."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            title TEXT NOT NULL,
            trigger TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'critical',
            description TEXT NOT NULL DEFAULT '',
            impact TEXT NOT NULL DEFAULT '',
            phase TEXT NOT NULL DEFAULT 'detect',
            status TEXT NOT NULL DEFAULT 'open',
            created_by TEXT NOT NULL DEFAULT 'system',
            detected_at TEXT NOT NULL,
            contained_at TEXT,
            diagnosed_at TEXT,
            repaired_at TEXT,
            verified_at TEXT,
            closed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_project
            ON incidents(project_id, status, severity, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_incidents_run
            ON incidents(run_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS incident_events (
            event_id TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_incident_events_incident
            ON incident_events(incident_id, created_at ASC);
        CREATE TABLE IF NOT EXISTS incident_team_members (
            incident_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'assigned',
            assigned_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(incident_id, agent_id),
            FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE,
            FOREIGN KEY(agent_id) REFERENCES agent_profiles(agent_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_incident_team_role
            ON incident_team_members(incident_id, role);
        CREATE TABLE IF NOT EXISTS postmortems (
            postmortem_id TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL UNIQUE,
            project_id TEXT,
            what_happened TEXT NOT NULL,
            impact TEXT NOT NULL DEFAULT '',
            timeline_json TEXT NOT NULL DEFAULT '[]',
            root_cause TEXT NOT NULL DEFAULT '',
            contributing_factors_json TEXT NOT NULL DEFAULT '[]',
            repair TEXT NOT NULL DEFAULT '',
            verification_json TEXT NOT NULL DEFAULT '[]',
            prevention_ideas_json TEXT NOT NULL DEFAULT '[]',
            follow_up_tasks_json TEXT NOT NULL DEFAULT '[]',
            lesson_memory_id TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(lesson_memory_id) REFERENCES experience_memories(id)
        );
        CREATE INDEX IF NOT EXISTS idx_postmortems_project
            ON postmortems(project_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS collaboration_quality (
            quality_id TEXT PRIMARY KEY,
            project_id TEXT,
            issue_type TEXT NOT NULL,
            signature TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            occurrences INTEGER NOT NULL DEFAULT 1,
            examples_json TEXT NOT NULL DEFAULT '[]',
            last_seen_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, signature)
        );
        CREATE INDEX IF NOT EXISTS idx_collaboration_quality_project
            ON collaboration_quality(project_id, occurrences DESC, updated_at DESC);
        CREATE TABLE IF NOT EXISTS owner_control_actions (
            action_id TEXT PRIMARY KEY,
            project_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'requested',
            requested_by TEXT NOT NULL DEFAULT 'human_owner',
            approved_by TEXT,
            reason TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            result_json TEXT NOT NULL DEFAULT '{}',
            requires_approval INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_owner_actions_project
            ON owner_control_actions(project_id, status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_owner_actions_pending
            ON owner_control_actions(status, requires_approval, created_at ASC);
        CREATE TABLE IF NOT EXISTS project_opportunities (
            opportunity_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            external_ref TEXT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            requirements_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'inbox',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source, external_ref)
        );
        CREATE INDEX IF NOT EXISTS idx_opportunities_status
            ON project_opportunities(status, updated_at DESC);
        """
    )

def _migration_11(database: sqlite3.Connection) -> None:
    """Persist a bounded company event stream for durable run reconstruction."""
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS company_events (
            event_id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            task_id TEXT,
            event_type TEXT NOT NULL,
            actor_role TEXT NOT NULL DEFAULT 'system',
            actor_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_company_events_project_time
            ON company_events(project_id, created_at ASC);
        CREATE INDEX IF NOT EXISTS idx_company_events_run_time
            ON company_events(run_id, created_at ASC);
        CREATE INDEX IF NOT EXISTS idx_company_events_type_time
            ON company_events(event_type, created_at ASC);
        """
    )


def _schema_version(database: sqlite3.Connection) -> int:
    columns = {
        str(row[1])
        for row in database.execute(
            f"PRAGMA table_info({_SCHEMA_VERSION_TABLE})"
        ).fetchall()
    }
    if "version" not in columns:
        return 0
    query = (
        "SELECT version FROM schema_version WHERE id = 1"
        if "id" in columns
        else "SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1"
    )
    row = database.execute(query).fetchone()
    try:
        return max(int(row[0]), 0) if row else 0
    except (TypeError, ValueError):
        return 0


def _record_schema_version(database: sqlite3.Connection, version: int) -> None:
    now = utc_now()
    columns = {
        str(row[1])
        for row in database.execute(
            f"PRAGMA table_info({_SCHEMA_VERSION_TABLE})"
        ).fetchall()
    }
    if "id" in columns:
        updated = database.execute(
            "UPDATE schema_version SET version = ?, applied_at = ? WHERE id = 1",
            (version, now),
        )
        if updated.rowcount == 0:
            database.execute(
                "INSERT INTO schema_version(id, version, applied_at) VALUES (1, ?, ?)",
                (version, now),
            )
        return
    database.execute("DELETE FROM schema_version")
    database.execute(
        "INSERT INTO schema_version(version, applied_at) VALUES (?, ?)",
        (version, now),
    )


def initialize_database(
    database_path: str | os.PathLike[str] | None = None,
) -> None:
    """Initialize or upgrade SQLite deterministically and without data loss.

    Migrations are additive and idempotent. Existing databases that predate
    ``schema_version`` are upgraded in place after their data is preserved.
    """
    with connect(database_path) as database:
        database.execute("PRAGMA journal_mode=WAL")
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        current = _schema_version(database)
        if current > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current} is newer than supported "
                f"version {SCHEMA_VERSION}."
            )

        migrations = ((1, _migration_1), (2, _migration_2), (3, _migration_3), (4, _migration_4), (5, _migration_5), (6, _migration_6), (7, _migration_7), (8, _migration_8), (9, _migration_9), (10, _migration_10), (11, _migration_11))
        for version, migration in migrations:
            if current < version:
                migration(database)
                _record_schema_version(database, version)
                current = version

        # Re-run additive definitions to repair partially-created databases even
        # when a previous process recorded a version early.
        _migration_1(database)
        _migration_2(database)
        _migration_3(database)
        _migration_4(database)
        _migration_5(database)
        _migration_6(database)
        _migration_7(database)
        _migration_8(database)
        _migration_9(database)
        _migration_10(database)
        _migration_11(database)
        if current < SCHEMA_VERSION:
            _record_schema_version(database, SCHEMA_VERSION)

def _row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())
    departments_raw = row["departments_json"] if "departments_json" in keys else "[]"
    try:
        departments = json.loads(departments_raw or "[]")
    except (TypeError, json.JSONDecodeError):
        departments = []
    if not isinstance(departments, list):
        departments = []
    return {
        "id": row["id"],
        "name": row["name"],
        "workspace": row["workspace"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "project_manager_id": row["project_manager_id"] if "project_manager_id" in keys else None,
        "engineering_manager_id": row["engineering_manager_id"] if "engineering_manager_id" in keys else None,
        "departments": [str(item) for item in departments if str(item).strip()],
        "phase": row["phase"] if "phase" in keys else "initiating",
        "priority": int(row["priority"]) if "priority" in keys and row["priority"] is not None else 50,
        "team_state": row["team_state"] if "team_state" in keys else "forming",
    }


def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "instruction": row["instruction"],
        "mode": row["mode"] if "mode" in row.keys() else "interactive",
        "status": row["status"],
        "plan": json.loads(row["plan_json"] or "[]"),
        "current_step": row["current_step"],
        "results": json.loads(row["results_json"] or "[]"),
        "approved_steps": json.loads(row["approved_steps_json"] or "[]"),
        "pending": json.loads(row["pending_json"]) if row["pending_json"] else None,
        "final_output": row["final_output"],
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "run_id": row["run_id"] if "run_id" in row.keys() else None,
        "lease_owner": row["lease_owner"] if "lease_owner" in row.keys() else None,
        "lease_token": row["lease_token"] if "lease_token" in row.keys() else None,
        "lease_expires_at": row["lease_expires_at"] if "lease_expires_at" in row.keys() else None,
        "heartbeat_at": row["heartbeat_at"] if "heartbeat_at" in row.keys() else None,
        "attempt_count": row["attempt_count"] if "attempt_count" in row.keys() else 0,
        "recovery_state": row["recovery_state"] if "recovery_state" in row.keys() else "new",
        "failure_kind": row["failure_kind"] if "failure_kind" in row.keys() else None,
        "provider": row["provider"] if "provider" in row.keys() else None,
        "fallback_provider": row["fallback_provider"] if "fallback_provider" in row.keys() else None,
        "retry_after": row["retry_after"] if "retry_after" in row.keys() else None,
        "last_checkpoint_ref": row["last_checkpoint_ref"] if "last_checkpoint_ref" in row.keys() else None,
    }


def create_project(name: str, workspace: str, *, database_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    project_id = str(uuid4())
    now = utc_now()
    with connect(database_path) as database:
        database.execute(
            "INSERT INTO projects(id, name, workspace, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, name, workspace, now, now),
        )
        row = database.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project(row)


def list_projects() -> list[dict[str, Any]]:
    with connect() as database:
        rows = database.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ).fetchall()

    return [_row_to_project(row) for row in rows]


def get_project(project_id: str) -> dict[str, Any] | None:
    with connect() as database:
        row = database.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    return _row_to_project(row) if row else None


def create_task(
    project_id: str,
    instruction: str,
    *,
    mode: str = "interactive",
) -> dict[str, Any]:
    if mode not in {"interactive", "autonomous"}:
        raise ValueError(f"Unsupported task mode: {mode}")

    task_id = str(uuid4())
    now = utc_now()

    with connect() as database:
        database.execute(
            """
            INSERT INTO agent_tasks(
                id, project_id, instruction, mode, status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'queued', ?, ?)
            """,
            (task_id, project_id, instruction, mode, now, now),
        )

        row = database.execute(
            "SELECT * FROM agent_tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return _row_to_task(row)


def get_task(task_id: str) -> dict[str, Any] | None:
    with connect() as database:
        row = database.execute(
            "SELECT * FROM agent_tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return _row_to_task(row) if row else None


def list_tasks(project_id: str | None = None) -> list[dict[str, Any]]:
    with connect() as database:
        if project_id:
            rows = database.execute(
                """
                SELECT * FROM agent_tasks
                WHERE project_id = ?
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        else:
            rows = database.execute(
                "SELECT * FROM agent_tasks ORDER BY created_at DESC"
            ).fetchall()

    return [_row_to_task(row) for row in rows]


def update_task(task_id: str, **changes: Any) -> dict[str, Any]:
    allowed = {
        "status",
        "plan",
        "current_step",
        "results",
        "approved_steps",
        "pending",
        "final_output",
        "error",
        "run_id",
        "lease_owner",
        "lease_token",
        "lease_expires_at",
        "heartbeat_at",
        "attempt_count",
        "recovery_state",
        "failure_kind",
        "provider",
        "fallback_provider",
        "retry_after",
        "last_checkpoint_ref",
    }

    assignments: list[str] = []
    values: list[Any] = []

    for key, value in changes.items():
        if key not in allowed:
            continue

        database_key = {
            "plan": "plan_json",
            "results": "results_json",
            "approved_steps": "approved_steps_json",
            "pending": "pending_json",
        }.get(key, key)

        if key in {"plan", "results", "approved_steps"}:
            value = json.dumps(value, ensure_ascii=False)
        elif key == "pending":
            value = (
                json.dumps(value, ensure_ascii=False)
                if value is not None
                else None
            )

        assignments.append(f"{database_key} = ?")
        values.append(value)

    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(task_id)

    with connect() as database:
        database.execute(
            f"""
            UPDATE agent_tasks
            SET {", ".join(assignments)}
            WHERE id = ?
            """,
            values,
        )

        row = database.execute(
            "SELECT * FROM agent_tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row and row["status"] in {"completed", "failed", "cancelled"}:
            _remember_terminal_task(database, row)

    if not row:
        raise KeyError(task_id)

    return _row_to_task(row)


def _remember_terminal_task(database: sqlite3.Connection, row: sqlite3.Row) -> None:
    """Persist a compact episodic memory whenever a task reaches a terminal state."""
    existing = database.execute(
        "SELECT 1 FROM agent_memories WHERE task_id = ? LIMIT 1",
        (row["id"],),
    ).fetchone()
    if existing:
        return

    status = str(row["status"])
    summary = str(row["final_output"] or row["error"] or f"Task {status}.").strip()
    try:
        plan = json.loads(row["plan_json"] or "[]")
        results = json.loads(row["results_json"] or "[]")
    except json.JSONDecodeError:
        plan, results = [], []

    changed_files: list[str] = []
    validations: list[str] = []
    failures: list[str] = []
    for item in results if isinstance(results, list) else []:
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        tool = str(outcome.get("tool") or step.get("tool") or "")
        path = str((step.get("arguments") or {}).get("path") or "").strip()
        if outcome.get("ok") and tool in {"write_file", "replace_text", "apply_patch"} and path:
            if path not in changed_files:
                changed_files.append(path)
        if outcome.get("ok") and tool == "run_terminal":
            command = str((step.get("arguments") or {}).get("command") or "").strip()
            if command:
                validations.append(command)
        if not outcome.get("ok") and not outcome.get("approval_required"):
            error = str(outcome.get("error") or "Tool failed.").strip()
            if error and error not in failures:
                failures.append(error)

    instruction_text = str(row["instruction"])
    for marker in ("LEARNED PROJECT MEMORY", "LEARNED MEMORY"):
        if marker in instruction_text:
            instruction_text = instruction_text.split(marker, 1)[0].rstrip()
            break

    changed_files = _bounded_memory_values(changed_files, limit=30, item_limit=512)
    validations = _bounded_memory_values(validations, limit=10)
    failures = _bounded_memory_values(failures, limit=10)
    detail = {
        "schema_version": "1.2",
        "instruction": instruction_text[:MEMORY_INSTRUCTION_LIMIT],
        "mode": str(row["mode"] if "mode" in row.keys() else "interactive"),
        "status": status,
        "step_count": len(plan) if isinstance(plan, list) else 0,
        "changed_files": changed_files,
        "validations": validations,
        "failures": failures,
    }
    now = utc_now()
    database.execute(
        """
        INSERT INTO agent_memories(
            id, project_id, task_id, kind, summary, detail_json,
            confidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            row["project_id"],
            row["id"],
            "success" if status == "completed" else status,
            summary[:2000],
            json.dumps(detail, ensure_ascii=False),
            1.0 if status == "completed" else 0.35,
            now,
        ),
    )


def search_memories(
    project_id: str,
    query: str | None = None,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    safe_limit = min(max(int(limit), 1), 50)
    terms = [term.casefold() for term in (query or "").split() if len(term) > 2][:6]

    with connect() as database:
        if terms:
            predicates = " OR ".join(
                "(lower(summary) LIKE ? OR lower(detail_json) LIKE ?)"
                for _ in terms
            )
            values: list[Any] = [project_id]
            for term in terms:
                pattern = f"%{term}%"
                values.extend([pattern, pattern])
            values.append(safe_limit)
            rows = database.execute(
                f"""
                SELECT * FROM agent_memories
                WHERE project_id = ? AND ({predicates})
                ORDER BY created_at DESC
                LIMIT ?
                """,
                values,
            ).fetchall()
        else:
            rows = database.execute(
                """
                SELECT * FROM agent_memories
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, safe_limit),
            ).fetchall()

        if rows:
            database.executemany(
                """
                UPDATE agent_memories
                SET last_used_at = ?, use_count = use_count + 1
                WHERE id = ?
                """,
                [(utc_now(), row["id"]) for row in rows],
            )

    memories: list[dict[str, Any]] = []
    for row in rows:
        try:
            detail = json.loads(row["detail_json"] or "{}")
        except json.JSONDecodeError:
            detail = {}
        if isinstance(detail, dict):
            if "instruction" in detail:
                detail["instruction"] = str(detail["instruction"])[:1_200]
            for key in ("changed_files", "validations", "failures"):
                value = detail.get(key)
                if isinstance(value, list):
                    detail[key] = [str(item)[:500] for item in value[:20]]
        memories.append({
            "id": row["id"],
            "project_id": row["project_id"],
            "task_id": row["task_id"],
            "kind": row["kind"],
            "summary": row["summary"],
            "detail": detail,
            "confidence": row["confidence"],
            "created_at": row["created_at"],
            "use_count": row["use_count"] + 1,
        })
    return memories


def create_autonomy_run(
    project_id: str,
    goal: str,
    requested_cycles: int,
) -> dict[str, Any]:
    run_id = str(uuid4())
    now = utc_now()
    with connect() as database:
        database.execute(
            """
            INSERT INTO autonomy_runs(
                id, project_id, goal, requested_cycles, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'queued', ?, ?)
            """,
            (run_id, project_id, goal, requested_cycles, now, now),
        )
    return get_autonomy_run(run_id)


def get_autonomy_run(run_id: str) -> dict[str, Any] | None:
    with connect() as database:
        row = database.execute(
            "SELECT * FROM autonomy_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "goal": row["goal"],
        "requested_cycles": row["requested_cycles"],
        "completed_cycles": row["completed_cycles"],
        "status": row["status"],
        "task_ids": json.loads(row["task_ids_json"] or "[]"),
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "current_stage": row["current_stage"] if "current_stage" in row.keys() else "queued",
        "recovery_state": row["recovery_state"] if "recovery_state" in row.keys() else "new",
        "lease_owner": row["lease_owner"] if "lease_owner" in row.keys() else None,
        "lease_token": row["lease_token"] if "lease_token" in row.keys() else None,
        "lease_expires_at": row["lease_expires_at"] if "lease_expires_at" in row.keys() else None,
        "heartbeat_at": row["heartbeat_at"] if "heartbeat_at" in row.keys() else None,
        "retry_count": row["retry_count"] if "retry_count" in row.keys() else 0,
        "failure_kind": row["failure_kind"] if "failure_kind" in row.keys() else None,
        "provider": row["provider"] if "provider" in row.keys() else None,
        "fallback_provider": row["fallback_provider"] if "fallback_provider" in row.keys() else None,
        "checkpoint_ref": row["checkpoint_ref"] if "checkpoint_ref" in row.keys() else None,
        "pending_approval": json.loads(row["pending_approval_json"] or "{}") if "pending_approval_json" in row.keys() and row["pending_approval_json"] else None,
        "last_recovery_at": row["last_recovery_at"] if "last_recovery_at" in row.keys() else None,
    }


def list_autonomy_runs(
    project_id: str | None = None,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return recent bounded self-improvement runs for monitoring clients."""
    safe_limit = min(max(int(limit), 1), 100)
    with connect() as database:
        if project_id:
            rows = database.execute(
                """
                SELECT * FROM autonomy_runs
                WHERE project_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (project_id, safe_limit),
            ).fetchall()
        else:
            rows = database.execute(
                """
                SELECT * FROM autonomy_runs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

    return [
        {
            "id": row["id"],
            "project_id": row["project_id"],
            "goal": row["goal"],
            "requested_cycles": row["requested_cycles"],
            "completed_cycles": row["completed_cycles"],
            "status": row["status"],
            "task_ids": json.loads(row["task_ids_json"] or "[]"),
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "current_stage": row["current_stage"] if "current_stage" in row.keys() else "queued",
            "recovery_state": row["recovery_state"] if "recovery_state" in row.keys() else "new",
            "lease_owner": row["lease_owner"] if "lease_owner" in row.keys() else None,
            "lease_token": row["lease_token"] if "lease_token" in row.keys() else None,
            "lease_expires_at": row["lease_expires_at"] if "lease_expires_at" in row.keys() else None,
            "heartbeat_at": row["heartbeat_at"] if "heartbeat_at" in row.keys() else None,
            "retry_count": row["retry_count"] if "retry_count" in row.keys() else 0,
            "failure_kind": row["failure_kind"] if "failure_kind" in row.keys() else None,
            "provider": row["provider"] if "provider" in row.keys() else None,
            "fallback_provider": row["fallback_provider"] if "fallback_provider" in row.keys() else None,
            "checkpoint_ref": row["checkpoint_ref"] if "checkpoint_ref" in row.keys() else None,
            "pending_approval": json.loads(row["pending_approval_json"] or "{}") if "pending_approval_json" in row.keys() and row["pending_approval_json"] else None,
            "last_recovery_at": row["last_recovery_at"] if "last_recovery_at" in row.keys() else None,
        }
        for row in rows
    ]


def update_autonomy_run(run_id: str, **changes: Any) -> dict[str, Any]:
    allowed = {
        "completed_cycles", "status", "task_ids", "error",
        "current_stage", "recovery_state", "lease_owner", "lease_token",
        "lease_expires_at", "heartbeat_at", "retry_count", "failure_kind",
        "provider", "fallback_provider", "checkpoint_ref",
        "pending_approval", "last_recovery_at",
    }
    assignments: list[str] = []
    values: list[Any] = []
    for key, value in changes.items():
        if key not in allowed:
            continue
        column = {
            "task_ids": "task_ids_json",
            "pending_approval": "pending_approval_json",
        }.get(key, key)
        if key in {"task_ids", "pending_approval"}:
            value = json.dumps(value, ensure_ascii=False)
        assignments.append(f"{column} = ?")
        values.append(value)
    if not assignments:
        return get_autonomy_run(run_id)
    assignments.append("updated_at = ?")
    values.extend([utc_now(), run_id])
    with connect() as database:
        database.execute(
            f"UPDATE autonomy_runs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
    return get_autonomy_run(run_id)


def _json_list(value: object) -> list[Any]:
    serialized = str(value or "[]")
    if len(serialized.encode("utf-8", errors="replace")) > MEMORY_JSON_MAX_BYTES:
        return []
    try:
        parsed = json.loads(serialized)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _row_to_subagent_handoff(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "project_id": row["project_id"],
        "task_id": row["task_id"],
        "role": row["role"],
        "section": row["section"],
        "schema_version": row["schema_version"],
        "status": row["status"],
        "summary": row["summary"],
        "evidence": _json_list(row["evidence_json"]),
        "changed_files": _json_list(row["changed_files_json"]),
        "validations": _json_list(row["validations_json"]),
        "blockers": _json_list(row["blockers_json"]),
        "next_action": row["next_action"],
        "confidence": float(row["confidence"] or 0),
        "previous_handoff_ids": _json_list(row["previous_handoff_ids_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_subagent_handoff(
    *,
    run_id: str,
    project_id: str,
    role: str,
    section: str,
    status: str = "queued",
    summary: str = "",
    task_id: str | None = None,
    schema_version: str = "1.0",
    evidence: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    changed_files: list[str] | tuple[str, ...] = (),
    validations: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    blockers: list[str] | tuple[str, ...] = (),
    next_action: str | None = None,
    confidence: float = 0.0,
    previous_handoff_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Persist one versioned specialist result on the run blackboard."""
    handoff_id = str(uuid4())
    now = utc_now()
    with connect() as database:
        database.execute(
            """
            INSERT INTO subagent_handoffs(
                id, run_id, project_id, task_id, role, section, schema_version,
                status, summary, evidence_json, changed_files_json,
                validations_json, blockers_json, next_action, confidence,
                previous_handoff_ids_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                handoff_id,
                run_id,
                project_id,
                task_id,
                str(role),
                str(section),
                str(schema_version or "1.0"),
                str(status or "queued"),
                str(summary or "")[:4_000],
                json.dumps(list(evidence)[:20], ensure_ascii=False),
                json.dumps([str(item) for item in list(changed_files)[:50]], ensure_ascii=False),
                json.dumps(list(validations)[:20], ensure_ascii=False),
                json.dumps([str(item) for item in list(blockers)[:20]], ensure_ascii=False),
                str(next_action)[:1_000] if next_action else None,
                max(0.0, min(float(confidence), 1.0)),
                json.dumps([str(item) for item in list(previous_handoff_ids)[:20]], ensure_ascii=False),
                now,
                now,
            ),
        )
    return get_subagent_handoff(handoff_id)


def get_subagent_handoff(handoff_id: str) -> dict[str, Any] | None:
    with connect() as database:
        row = database.execute(
            "SELECT * FROM subagent_handoffs WHERE id = ?",
            (handoff_id,),
        ).fetchone()
    return _row_to_subagent_handoff(row) if row else None


def list_subagent_handoffs(
    run_id: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    safe_limit = min(max(int(limit), 1), 200)
    with connect() as database:
        rows = database.execute(
            """
            SELECT * FROM subagent_handoffs
            WHERE run_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (run_id, safe_limit),
        ).fetchall()
    return [_row_to_subagent_handoff(row) for row in rows]


def update_subagent_handoff(handoff_id: str, **changes: Any) -> dict[str, Any] | None:
    allowed = {
        "task_id", "status", "summary", "evidence", "changed_files",
        "validations", "blockers", "next_action", "confidence",
        "previous_handoff_ids",
    }
    assignments: list[str] = []
    values: list[Any] = []
    json_columns = {
        "evidence": "evidence_json",
        "changed_files": "changed_files_json",
        "validations": "validations_json",
        "blockers": "blockers_json",
        "previous_handoff_ids": "previous_handoff_ids_json",
    }
    for key, value in changes.items():
        if key not in allowed:
            continue
        column = json_columns.get(key, key)
        if key in json_columns:
            if key in {"changed_files", "blockers", "previous_handoff_ids"}:
                value = [str(item) for item in list(value or [])[:50]]
            else:
                value = list(value or [])[:20]
            value = json.dumps(value, ensure_ascii=False)
        elif key == "summary":
            value = str(value or "")[:4_000]
        elif key == "next_action":
            value = str(value)[:1_000] if value else None
        elif key == "confidence":
            value = max(0.0, min(float(value), 1.0))
        assignments.append(f"{column} = ?")
        values.append(value)
    if not assignments:
        return get_subagent_handoff(handoff_id)
    assignments.append("updated_at = ?")
    values.extend([utc_now(), handoff_id])
    with connect() as database:
        database.execute(
            f"UPDATE subagent_handoffs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
    return get_subagent_handoff(handoff_id)
