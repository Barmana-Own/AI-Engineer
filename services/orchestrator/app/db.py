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
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_database() -> None:
    with connect() as database:
        database.execute("PRAGMA journal_mode=WAL")
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
                mode TEXT NOT NULL DEFAULT 'interactive',
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

            CREATE INDEX IF NOT EXISTS idx_agent_memories_project
                ON agent_memories(project_id, created_at DESC);

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

            CREATE INDEX IF NOT EXISTS idx_subagent_handoffs_run
                ON subagent_handoffs(run_id, created_at ASC);

            CREATE INDEX IF NOT EXISTS idx_subagent_handoffs_project
                ON subagent_handoffs(project_id, updated_at DESC);
            """
        )

        task_columns = {
            str(row[1])
            for row in database.execute("PRAGMA table_info(agent_tasks)").fetchall()
        }
        if "mode" not in task_columns:
            database.execute(
                "ALTER TABLE agent_tasks ADD COLUMN mode TEXT NOT NULL DEFAULT 'interactive'"
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

    validations = list(dict.fromkeys(validations))
    failures = list(dict.fromkeys(failures))
    detail = {
        "instruction": instruction_text[:4_000],
        "mode": str(row["mode"] if "mode" in row.keys() else "interactive"),
        "status": status,
        "step_count": len(plan) if isinstance(plan, list) else 0,
        "changed_files": changed_files[:30],
        "validations": validations[-10:],
        "failures": failures[-10:],
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
        }
        for row in rows
    ]


def update_autonomy_run(run_id: str, **changes: Any) -> dict[str, Any]:
    allowed = {"completed_cycles", "status", "task_ids", "error"}
    assignments: list[str] = []
    values: list[Any] = []
    for key, value in changes.items():
        if key not in allowed:
            continue
        column = "task_ids_json" if key == "task_ids" else key
        if key == "task_ids":
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
    try:
        parsed = json.loads(str(value or "[]"))
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
