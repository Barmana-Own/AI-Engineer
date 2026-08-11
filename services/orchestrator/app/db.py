from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DATABASE_PATH = Path("F:/AI-Engineer/data/orchestrator/orchestrator.db")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_database() -> None:
    with connect() as database:
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

            CREATE INDEX IF NOT EXISTS idx_agent_tasks_project
                ON agent_tasks(project_id);

            CREATE INDEX IF NOT EXISTS idx_agent_tasks_status
                ON agent_tasks(status);
            """
        )


def _row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "workspace": row["workspace"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "instruction": row["instruction"],
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
    }


def create_project(name: str, workspace: str) -> dict[str, Any]:
    project_id = str(uuid4())
    now = utc_now()

    with connect() as database:
        database.execute(
            """
            INSERT INTO projects(id, name, workspace, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, name, workspace, now, now),
        )

        row = database.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

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


def create_task(project_id: str, instruction: str) -> dict[str, Any]:
    task_id = str(uuid4())
    now = utc_now()

    with connect() as database:
        database.execute(
            """
            INSERT INTO agent_tasks(
                id, project_id, instruction, status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, 'queued', ?, ?)
            """,
            (task_id, project_id, instruction, now, now),
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

    if not row:
        raise KeyError(task_id)

    return _row_to_task(row)