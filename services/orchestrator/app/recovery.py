from __future__ import annotations

import json
import os
import socket
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app import db
from app.memory.sanitizer import sanitize_text

ACTIVE_TASK_STATUSES = frozenset(
    {"queued", "planning", "running", "awaiting_approval", "needs_verification"}
)
TERMINAL_TASK_STATUSES = frozenset({"completed", "failed", "cancelled"})
WAITING_TASK_STATUSES = frozenset(
    {"waiting_provider", "waiting_local_agent", "waiting_worker", "waiting_dependency"}
)
ACTIVE_RUN_STATUSES = frozenset(
    {
        "queued",
        "planning",
        "running",
        "awaiting_approval",
        "waiting_dependency",
        "recovery_required",
    }
)
TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled"})


class LeaseConflictError(RuntimeError):
    """Raised when another live worker owns a task lease."""


class RecoveryRequiredError(RuntimeError):
    """Raised when a task/run needs verification before it can be resumed."""


def _utc(value: str | datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value).strip()
        if not text:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            result = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _utc()).isoformat()


def _database_path(database_path: str | os.PathLike[str] | None = None) -> str | os.PathLike[str] | None:
    return database_path if database_path is not None else db.DATABASE_PATH


def _owner_id(owner_id: str | None = None) -> str:
    return str(owner_id or os.getenv("AI_ENGINEER_WORKER_ID") or f"{socket.gethostname()}:{os.getpid()}")


def _safe_detail(value: Any, limit: int = 2_000) -> str:
    clean, _ = sanitize_text(str(value or ""), max_chars=limit)
    return clean


def _row_json(row: sqlite3.Row | None, column: str, fallback: Any = None) -> Any:
    if row is None or column not in row.keys():
        return fallback
    value = row[column]
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _task_row(database: sqlite3.Connection, task_id: str) -> sqlite3.Row | None:
    return database.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()


def _run_row(database: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return database.execute("SELECT * FROM autonomy_runs WHERE id = ?", (run_id,)).fetchone()


def _lease_row(database: sqlite3.Connection, task_id: str) -> sqlite3.Row | None:
    return database.execute(
        "SELECT * FROM execution_leases WHERE task_id = ? ORDER BY acquired_at DESC LIMIT 1",
        (task_id,),
    ).fetchone()


def _is_expired(value: str | None, now: datetime, stale_after_seconds: int = 900) -> bool:
    timestamp = _utc(value)
    if timestamp == datetime.min.replace(tzinfo=timezone.utc):
        return True
    return timestamp <= now - timedelta(seconds=max(int(stale_after_seconds), 1))


def classify_dependency_error(error: BaseException | str) -> tuple[str, str, str] | None:
    """Map transient model/local worker failures to a durable dependency class."""
    status = getattr(error, "status_code", None)
    detail = getattr(error, "detail", None)
    text = _safe_detail(detail if detail is not None else error, 1_500)
    lowered = text.casefold()
    if any(
        marker in lowered
        for marker in (
            "local agent",
            "local-agent",
            "localhost:8011",
            ":8011/",
            "file tool",
            "terminal tool",
            "process tool",
            "connection refused",
        )
    ):
        return ("local_agent", "temporary_unavailable", text)
    if any(
        marker in lowered
        for marker in (
            "model gateway",
            "model-gateway",
            "provider",
            "chat/completions",
            "localhost:8010",
            ":8010/",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "rate limit",
            "upstream",
        )
    ) or status in {502, 503, 504}:
        return ("provider", "temporary_unavailable", text)
    return None


def classify_task(
    task: dict[str, Any] | sqlite3.Row,
    *,
    now: datetime | None = None,
    stale_after_seconds: int = 900,
) -> str:
    current = now or _utc()
    status = str(task["status"] or "").casefold()
    if status in TERMINAL_TASK_STATUSES:
        return "completed" if status == "completed" else "failed"
    if status in WAITING_TASK_STATUSES:
        return "waiting_for_dependency"
    if status == "awaiting_approval":
        return "waiting_for_approval"
    if status in {"queued", "planning"}:
        return "safe_to_resume"
    if status not in ACTIVE_TASK_STATUSES:
        return "orphaned"
    heartbeat = task["heartbeat_at"] if "heartbeat_at" in task.keys() else None
    expires = task["lease_expires_at"] if "lease_expires_at" in task.keys() else None
    stale_heartbeat = _is_expired(heartbeat, current, stale_after_seconds)
    expired_lease = bool(expires) and _utc(expires) <= current
    if not stale_heartbeat and not expired_lease:
        return "active"
    recovery_state = str(task["recovery_state"] or "") if "recovery_state" in task.keys() else ""
    results = _row_json(task, "results_json", [])
    checkpoint = task["last_checkpoint_ref"] if "last_checkpoint_ref" in task.keys() else None
    if expired_lease or recovery_state in {"active", "needs_verification"} or results or checkpoint:
        return "needs_verification"
    return "safe_to_resume"


def _record_event(
    database: sqlite3.Connection,
    *,
    event_type: str,
    idempotency_key: str,
    run_id: str | None = None,
    task_id: str | None = None,
    from_state: str | None = None,
    to_state: str | None = None,
    classification: str | None = None,
    detail: dict[str, Any] | None = None,
) -> bool:
    try:
        database.execute(
            """
            INSERT INTO recovery_events(
                id, idempotency_key, run_id, task_id, event_type,
                from_state, to_state, classification, detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                idempotency_key,
                run_id,
                task_id,
                event_type,
                from_state,
                to_state,
                classification,
                json.dumps(detail or {}, ensure_ascii=False),
                db.utc_now(),
            ),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def acquire_task_lease(
    task_id: str,
    *,
    owner_id: str | None = None,
    ttl_seconds: int = 600,
    run_id: str | None = None,
    database_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    owner = _owner_id(owner_id)
    now = _utc()
    expires = now + timedelta(seconds=max(int(ttl_seconds), 30))
    token = str(uuid4())
    with db.connect(_database_path(database_path)) as database:
        database.execute("BEGIN IMMEDIATE")
        task = _task_row(database, task_id)
        if task is None:
            raise KeyError(task_id)
        if str(task["status"]) in TERMINAL_TASK_STATUSES:
            raise RecoveryRequiredError(f"Task {task_id} is already {task['status']}.")
        existing = _lease_row(database, task_id)
        if existing and str(existing["state"]) == "active" and _utc(existing["expires_at"]) > now:
            if str(existing["owner_id"]) == owner:
                return {
                    "task_id": task_id,
                    "run_id": existing["run_id"],
                    "owner_id": owner,
                    "lease_token": existing["lease_token"],
                    "expires_at": existing["expires_at"],
                    "state": "active",
                    "idempotent": True,
                }
            raise LeaseConflictError(f"Task {task_id} is leased by another worker.")
        if existing:
            database.execute(
                "UPDATE execution_leases SET state = 'expired', released_at = ? WHERE task_id = ? AND state = 'active'",
                (db.utc_now(), task_id),
            )
        database.execute(
            """
            INSERT INTO execution_leases(
                resource, task_id, run_id, owner_id, lease_token, state,
                acquired_at, heartbeat_at, expires_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            ON CONFLICT(resource) DO UPDATE SET
                task_id=excluded.task_id, run_id=excluded.run_id,
                owner_id=excluded.owner_id, lease_token=excluded.lease_token,
                state='active', acquired_at=excluded.acquired_at,
                heartbeat_at=excluded.heartbeat_at, expires_at=excluded.expires_at,
                released_at=NULL, last_error=NULL
            """,
            (
                f"task:{task_id}",
                task_id,
                run_id or (task["run_id"] if "run_id" in task.keys() else None),
                owner,
                token,
                _iso(now),
                _iso(now),
                _iso(expires),
                json.dumps({"worker": owner}, ensure_ascii=False),
            ),
        )
        database.execute(
            """
            UPDATE agent_tasks
            SET lease_owner = ?, lease_token = ?, lease_expires_at = ?,
                heartbeat_at = ?, recovery_state = 'active',
                attempt_count = COALESCE(attempt_count, 0) + 1,
                run_id = COALESCE(run_id, ?), updated_at = ?
            WHERE id = ?
            """,
            (owner, token, _iso(expires), _iso(now), run_id, _iso(now), task_id),
        )
        _record_event(
            database,
            event_type="lease_acquired",
            idempotency_key=f"lease:{task_id}:{token}",
            run_id=run_id or (task["run_id"] if "run_id" in task.keys() else None),
            task_id=task_id,
            from_state=str(task["status"]),
            to_state="running",
            classification="safe_to_resume",
            detail={"owner_id": owner},
        )
    return {
        "task_id": task_id,
        "run_id": run_id or (task["run_id"] if "run_id" in task.keys() else None),
        "owner_id": owner,
        "lease_token": token,
        "expires_at": _iso(expires),
        "state": "active",
        "idempotent": False,
    }


def heartbeat_task_lease(
    task_id: str,
    lease_token: str,
    *,
    ttl_seconds: int = 600,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    now = _utc()
    expires = now + timedelta(seconds=max(int(ttl_seconds), 30))
    with db.connect(_database_path(database_path)) as database:
        updated = database.execute(
            """
            UPDATE execution_leases
            SET heartbeat_at = ?, expires_at = ?
            WHERE task_id = ? AND lease_token = ? AND state = 'active'
            """,
            (_iso(now), _iso(expires), task_id, str(lease_token)),
        )
        if updated.rowcount != 1:
            return False
        database.execute(
            """
            UPDATE agent_tasks
            SET heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
            WHERE id = ? AND lease_token = ?
            """,
            (_iso(now), _iso(expires), _iso(now), task_id, str(lease_token)),
        )
    return True


def release_task_lease(
    task_id: str,
    lease_token: str,
    *,
    error: str | None = None,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    now = db.utc_now()
    with db.connect(_database_path(database_path)) as database:
        updated = database.execute(
            """
            UPDATE execution_leases
            SET state = 'released', released_at = ?, last_error = ?
            WHERE task_id = ? AND lease_token = ? AND state = 'active'
            """,
            (now, _safe_detail(error) if error else None, task_id, str(lease_token)),
        )
        if updated.rowcount != 1:
            return False
        database.execute(
            """
            UPDATE agent_tasks
            SET lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
                heartbeat_at = NULL, updated_at = ?
            WHERE id = ? AND lease_token = ?
            """,
            (now, task_id, str(lease_token)),
        )
    return True


def record_run_heartbeat(
    run_id: str,
    *,
    stage: str | None = None,
    lease_token: str | None = None,
    owner_id: str | None = None,
    ttl_seconds: int = 600,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    now = _utc()
    expires = now + timedelta(seconds=max(int(ttl_seconds), 30))
    assignments = ["heartbeat_at = ?", "updated_at = ?"]
    values: list[Any] = [_iso(now), _iso(now)]
    if stage:
        assignments.append("current_stage = ?")
        values.append(str(stage)[:200])
    if owner_id:
        assignments.append("lease_owner = ?")
        values.append(_owner_id(owner_id))
    if lease_token:
        assignments.append("lease_token = ?")
        values.append(str(lease_token))
        assignments.append("lease_expires_at = ?")
        values.append(_iso(expires))
    values.append(run_id)
    with db.connect(_database_path(database_path)) as database:
        updated = database.execute(
            f"UPDATE autonomy_runs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        if updated.rowcount != 1:
            return False
        if lease_token:
            database.execute(
                """
                UPDATE execution_leases SET heartbeat_at = ?, expires_at = ?
                WHERE run_id = ? AND lease_token = ? AND state = 'active'
                """,
                (_iso(now), _iso(expires), run_id, str(lease_token)),
            )
    return True


def pause_task_for_dependency(
    task_id: str,
    dependency: str,
    error: str | BaseException,
    *,
    run_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    fallback_provider: str | None = None,
    retry_after_seconds: int = 30,
    database_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    clean_error = _safe_detail(error)
    dependency_name = str(dependency or "worker").casefold()
    status = {
        "provider": "waiting_provider",
        "local_agent": "waiting_local_agent",
        "worker": "waiting_worker",
    }.get(dependency_name, "waiting_dependency")
    now = _utc()
    retry_at = now + timedelta(seconds=max(int(retry_after_seconds), 1))
    with db.connect(_database_path(database_path)) as database:
        task = _task_row(database, task_id)
        if task is None:
            raise KeyError(task_id)
        previous = str(task["status"])
        database.execute(
            """
            UPDATE agent_tasks
            SET status = ?, error = ?, failure_kind = 'temporary_dependency',
                recovery_state = 'waiting_for_dependency', retry_after = ?,
                run_id = COALESCE(run_id, ?), updated_at = ?
            WHERE id = ?
            """,
            (status, clean_error, _iso(retry_at), run_id, _iso(now), task_id),
        )
        if dependency_name in {"provider", "local_agent"}:
            database.execute(
                """
                INSERT INTO provider_failures(
                    id, run_id, task_id, dependency, provider, model,
                    error_code, error_detail, fallback_provider, retry_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    run_id or (task["run_id"] if "run_id" in task.keys() else None),
                    task_id,
                    dependency_name,
                    provider,
                    model,
                    "temporary_unavailable",
                    clean_error,
                    fallback_provider,
                    int(task["attempt_count"] or 0) if "attempt_count" in task.keys() else 0,
                    _iso(now),
                ),
            )
        _record_event(
            database,
            event_type="dependency_paused",
            idempotency_key=f"dependency:{task_id}:{status}:{clean_error[:120]}",
            run_id=run_id or (task["run_id"] if "run_id" in task.keys() else None),
            task_id=task_id,
            from_state=previous,
            to_state=status,
            classification="waiting_for_dependency",
            detail={
                "dependency": dependency_name,
                "retry_after": _iso(retry_at),
                "provider": provider,
                "fallback_provider": fallback_provider,
            },
        )
    return db.get_task(task_id)


def requeue_waiting_task(
    task_id: str,
    *,
    force: bool = False,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    now = _utc()
    with db.connect(_database_path(database_path)) as database:
        task = _task_row(database, task_id)
        if task is None:
            return False
        status = str(task["status"])
        retry_after = task["retry_after"] if "retry_after" in task.keys() else None
        if status not in WAITING_TASK_STATUSES:
            return status in {"queued", "planning"}
        if not force and retry_after and _utc(retry_after) > now:
            return False
        updated = database.execute(
            """
            UPDATE agent_tasks
            SET status = 'queued', recovery_state = 'safe_to_resume',
                failure_kind = NULL, retry_after = NULL, error = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (_iso(now), task_id),
        )
        if updated.rowcount:
            _record_event(
                database,
                event_type="dependency_requeued",
                idempotency_key=f"requeue:{task_id}:{retry_after or 'none'}",
                run_id=task["run_id"] if "run_id" in task.keys() else None,
                task_id=task_id,
                from_state=status,
                to_state="queued",
                classification="safe_to_resume",
            )
            return True
    return False


def recover_incomplete_runs(
    *,
    database_path: str | os.PathLike[str] | None = None,
    now: datetime | None = None,
    stale_after_seconds: int = 900,
) -> list[dict[str, Any]]:
    current = now or _utc()
    reports: list[dict[str, Any]] = []
    with db.connect(_database_path(database_path)) as database:
        database.execute(
            """
            UPDATE execution_leases
            SET state = 'expired', released_at = COALESCE(released_at, ?)
            WHERE state = 'active' AND expires_at <= ?
            """,
            (_iso(current), _iso(current)),
        )
        rows = database.execute(
            "SELECT * FROM autonomy_runs WHERE status NOT IN ('completed', 'failed', 'cancelled')"
        ).fetchall()
        for run in rows:
            task_ids = _row_json(run, "task_ids_json", [])
            if not isinstance(task_ids, list):
                task_ids = []
            classifications: list[dict[str, Any]] = []
            for raw_task_id in task_ids:
                task_id = str(raw_task_id)
                task = _task_row(database, task_id)
                if task is None:
                    classifications.append({"task_id": task_id, "classification": "orphaned"})
                    continue
                classification = classify_task(
                    task, now=current, stale_after_seconds=stale_after_seconds
                )
                classifications.append({"task_id": task_id, "classification": classification})
                old_status = str(task["status"])
                if classification == "safe_to_resume":
                    database.execute(
                        """
                        UPDATE agent_tasks
                        SET status = 'queued', recovery_state = 'safe_to_resume',
                            lease_owner = NULL, lease_token = NULL,
                            lease_expires_at = NULL, heartbeat_at = NULL,
                            updated_at = ?
                        WHERE id = ? AND status NOT IN ('completed', 'failed', 'cancelled')
                        """,
                        (_iso(current), task_id),
                    )
                elif classification == "needs_verification":
                    database.execute(
                        """
                        UPDATE agent_tasks
                        SET status = 'needs_verification', recovery_state = 'needs_verification',
                            lease_owner = NULL, lease_token = NULL,
                            lease_expires_at = NULL, heartbeat_at = NULL,
                            updated_at = ?
                        WHERE id = ? AND status NOT IN ('completed', 'failed', 'cancelled')
                        """,
                        (_iso(current), task_id),
                    )
                _record_event(
                    database,
                    event_type="startup_recovery",
                    idempotency_key=f"startup:{run['id']}:{task_id}:{current.date().isoformat()}:{classification}",
                    run_id=run["id"],
                    task_id=task_id,
                    from_state=old_status,
                    to_state="needs_verification" if classification == "needs_verification" else old_status,
                    classification=classification,
                    detail={"stale_after_seconds": stale_after_seconds},
                )
            counts = {item["classification"] for item in classifications}
            if "needs_verification" in counts or "orphaned" in counts:
                new_status, recovery_state = "recovery_required", "needs_verification"
            elif "waiting_for_dependency" in counts:
                new_status, recovery_state = "waiting_dependency", "waiting_for_dependency"
            else:
                new_status, recovery_state = "queued", "safe_to_resume"
            previous_run_status = str(run["status"])
            database.execute(
                """
                UPDATE autonomy_runs
                SET status = ?, recovery_state = ?, last_recovery_at = ?,
                    heartbeat_at = ?, current_stage = CASE
                        WHEN ? = 'recovery_required' THEN 'recovery'
                        ELSE current_stage
                    END, updated_at = ?
                WHERE id = ?
                """,
                (
                    new_status,
                    recovery_state,
                    _iso(current),
                    _iso(current),
                    new_status,
                    _iso(current),
                    run["id"],
                ),
            )
            _record_event(
                database,
                event_type="run_recovered",
                idempotency_key=f"run-recovery:{run['id']}:{current.date().isoformat()}:{new_status}",
                run_id=run["id"],
                from_state=previous_run_status,
                to_state=new_status,
                classification=recovery_state,
                detail={"tasks": classifications},
            )
            reports.append(
                {
                    "run_id": run["id"],
                    "previous_status": previous_run_status,
                    "status": new_status,
                    "recovery_state": recovery_state,
                    "tasks": classifications,
                }
            )
    return reports


def resume_run(
    run_id: str,
    *,
    verify: bool = False,
    database_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    with db.connect(_database_path(database_path)) as database:
        run = _run_row(database, run_id)
        if run is None:
            return None
        status = str(run["status"])
        if status in TERMINAL_RUN_STATUSES:
            return db.get_autonomy_run(run_id)
        # A queued run already normalized by recovery is safe to resume and
        # must remain idempotent when a caller retries the resume request.
        if (
            status == "queued"
            and str(run["recovery_state"] or "") == "safe_to_resume"
        ):
            return db.get_autonomy_run(run_id)
        if status == "recovery_required" and not verify:
            raise RecoveryRequiredError(
                f"Run {run_id} requires verification before resume."
            )
        task_ids = _row_json(run, "task_ids_json", [])
        if not isinstance(task_ids, list):
            task_ids = []
        for task_id in task_ids:
            task = _task_row(database, str(task_id))
            if task is None:
                continue
            task_status = str(task["status"])
            if task_status == "needs_verification" and not verify:
                raise RecoveryRequiredError(
                    f"Task {task_id} requires verification before resume."
                )
            if task_status == "needs_verification":
                database.execute(
                    """
                    UPDATE agent_tasks
                    SET status = 'queued', recovery_state = 'safe_to_resume',
                        failure_kind = NULL, error = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (db.utc_now(), task_id),
                )
            elif task_status in WAITING_TASK_STATUSES:
                retry_after = task["retry_after"] if "retry_after" in task.keys() else None
                if retry_after and _utc(retry_after) > _utc():
                    continue
                database.execute(
                    """
                    UPDATE agent_tasks
                    SET status = 'queued', recovery_state = 'safe_to_resume',
                        failure_kind = NULL, retry_after = NULL, error = NULL,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (db.utc_now(), task_id),
                )
        now = db.utc_now()
        database.execute(
            """
            UPDATE autonomy_runs
            SET status = 'queued', recovery_state = 'safe_to_resume',
                current_stage = 'queued', last_recovery_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, run_id),
        )
        _record_event(
            database,
            event_type="run_resumed",
            idempotency_key=f"resume:{run_id}:{run['last_recovery_at'] or run['updated_at']}:{verify}",
            run_id=run_id,
            from_state=status,
            to_state="queued",
            classification="safe_to_resume",
            detail={"verified": verify},
        )
    return db.get_autonomy_run(run_id)


def get_recovery_status(
    run_id: str | None = None,
    *,
    database_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    with db.connect(_database_path(database_path)) as database:
        if run_id:
            runs = [_run_row(database, run_id)]
        else:
            runs = database.execute(
                "SELECT * FROM autonomy_runs ORDER BY updated_at DESC LIMIT 100"
            ).fetchall()
        output: list[dict[str, Any]] = []
        for run in runs:
            if run is None:
                continue
            task_ids = _row_json(run, "task_ids_json", [])
            tasks = []
            for task_id in task_ids if isinstance(task_ids, list) else []:
                task = _task_row(database, str(task_id))
                if task is None:
                    tasks.append({"id": task_id, "classification": "orphaned"})
                    continue
                item = {key: task[key] for key in task.keys() if key in {
                    "id", "project_id", "status", "run_id", "lease_owner",
                    "lease_expires_at", "heartbeat_at", "recovery_state",
                    "failure_kind", "retry_after", "attempt_count", "error",
                }}
                item["classification"] = classify_task(task)
                tasks.append(item)
            output.append(
                {
                    "run_id": run["id"],
                    "project_id": run["project_id"],
                    "status": run["status"],
                    "recovery_state": run["recovery_state"] if "recovery_state" in run.keys() else "new",
                    "current_stage": run["current_stage"] if "current_stage" in run.keys() else None,
                    "tasks": tasks,
                    "heartbeat_at": run["heartbeat_at"] if "heartbeat_at" in run.keys() else None,
                    "last_recovery_at": run["last_recovery_at"] if "last_recovery_at" in run.keys() else None,
                }
            )
    return {"runs": output}
