
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from app import db
from app.coordination import project_management
from app.memory.sanitizer import sanitize_memory

OWNER_ACTIONS = {
    "start_project",
    "pause_project",
    "resume_project",
    "cancel_project",
    "change_priority",
    "request_report",
    "approve_major_decision",
    "reject_major_decision",
    "request_review",
}
HIGH_RISK_ACTIONS = {
    "production_deployment",
    "remote_publication",
    "destructive_infrastructure",
    "credential_sensitive_operation",
    "external_commitment",
    "financial_commitment",
}


@dataclass(frozen=True)
class ProjectOpportunity:
    opportunity_id: str
    source: str
    external_ref: str | None
    title: str
    summary: str
    requirements: tuple[str, ...]
    status: str
    created_at: str
    updated_at: str
    brief: dict[str, object] = field(default_factory=dict)
    qualification: dict[str, object] = field(default_factory=dict)
    owner_gate_status: str = "not_required"
    converted_project_id: str | None = None
    converted_at: str | None = None
    last_action: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ClientMessage:
    source: str
    external_ref: str | None
    body: str
    received_at: str


@dataclass(frozen=True)
class ProjectProposal:
    opportunity_id: str
    scope: str
    risks: tuple[str, ...] = ()
    status: str = "draft"


@dataclass(frozen=True)
class ClientRequirement:
    opportunity_id: str
    text: str
    priority: int = 50


@dataclass(frozen=True)
class ClientApproval:
    opportunity_id: str
    approved: bool
    actor: str
    decided_at: str


def _ensure(path: str | Path | None) -> None:
    db.initialize_database(path)


def _now() -> str:
    return db.utc_now()


def _json(value: object) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _load(value: object, fallback: object) -> object:
    try:
        return json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _clean_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    _, content, _, _ = sanitize_memory("", payload or {}, [])
    return content


def _action(row) -> dict[str, object]:
    return {
        "action_id": row["action_id"],
        "project_id": row["project_id"],
        "action": row["action"],
        "status": row["status"],
        "requested_by": row["requested_by"],
        "approved_by": row["approved_by"],
        "reason": row["reason"],
        "payload": _load(row["payload_json"], {}),
        "result": _load(row["result_json"], {}),
        "requires_approval": bool(row["requires_approval"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "resolved_at": row["resolved_at"],
    }


def _apply_action(
    action: str,
    project_id: str | None,
    payload: dict[str, Any],
    *,
    action_id: str,
    database_path: str | Path | None,
) -> dict[str, object]:
    result: dict[str, object] = {"action_id": action_id, "applied": True}
    if action in {"request_report", "request_review", "approve_major_decision", "reject_major_decision"}:
        result["execution"] = "recorded_for_supervisor"
        return result
    if not project_id:
        raise ValueError(f"{action} requires a project_id")
    state = project_management.get_project_state(project_id, database_path=database_path)
    if not state:
        raise KeyError(project_id)
    if action == "start_project":
        target = "requirements" if state["phase"] == "intake" else str(state["phase"])
        if target != state["phase"]:
            project_management.transition_project_phase(
                project_id,
                target,
                actor_role="human_owner",
                evidence=["human owner start_project action"],
                database_path=database_path,
            )
        result["phase"] = target
    elif action == "pause_project":
        if state["phase"] not in {"paused", "completed", "cancelled"}:
            result["previous_phase"] = state["phase"]
            project_management.transition_project_phase(
                project_id,
                "paused",
                actor_role="human_owner",
                evidence=["human owner pause_project action"],
                database_path=database_path,
            )
        else:
            result["previous_phase"] = state["phase"]
    elif action == "resume_project":
        if state["phase"] == "paused":
            target = str(payload.get("resume_phase") or "requirements")
            if target == "paused":
                target = "requirements"
            project_management.transition_project_phase(
                project_id,
                target,
                actor_role="human_owner",
                evidence=["human owner resume_project action"],
                database_path=database_path,
            )
            result["phase"] = target
        else:
            result["phase"] = state["phase"]
    elif action == "cancel_project":
        if state["phase"] not in {"completed", "cancelled"}:
            project_management.transition_project_phase(
                project_id,
                "cancelled",
                actor_role="human_owner",
                evidence=["human owner cancel_project action"],
                database_path=database_path,
            )
        result["phase"] = "cancelled"
    elif action == "change_priority":
        try:
            priority = max(0, min(100, int(payload.get("priority"))))
        except (TypeError, ValueError) as exc:
            raise ValueError("change_priority requires integer payload.priority") from exc
        with db.connect(database_path) as database:
            database.execute(
                "UPDATE projects SET priority=?, updated_at=? WHERE id=?",
                (priority, _now(), project_id),
            )
        result["priority"] = priority
    else:
        raise ValueError("unsupported owner action")
    return result


def request_owner_action(
    action: str,
    *,
    project_id: str | None = None,
    reason: str = "",
    payload: dict[str, Any] | None = None,
    requested_by: str = "human_owner",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    action = str(action).strip().lower()
    if action not in OWNER_ACTIONS | HIGH_RISK_ACTIONS:
        raise ValueError("unsupported owner action")
    if requested_by != "human_owner":
        raise PermissionError("only the Human Owner can request company actions")
    if project_id and project_management.get_project_state(project_id, database_path=database_path) is None:
        raise KeyError(project_id)
    clean_payload = _clean_payload(payload)
    requires = action in HIGH_RISK_ACTIONS
    status = "pending_approval" if requires else "requested"
    action_id, now = str(uuid4()), _now()
    with db.connect(database_path) as database:
        database.execute(
            """
            INSERT INTO owner_control_actions(
                action_id, project_id, action, status, requested_by, reason,
                payload_json, result_json, requires_approval, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, ?)
            """,
            (
                action_id,
                project_id,
                action,
                status,
                requested_by,
                str(reason or "")[:4000],
                _json(clean_payload),
                int(requires),
                now,
                now,
            ),
        )
    if not requires:
        result = _apply_action(
            action,
            project_id,
            clean_payload,
            action_id=action_id,
            database_path=database_path,
        )
        with db.connect(database_path) as database:
            database.execute(
                """
                UPDATE owner_control_actions
                SET status='applied', result_json=?, updated_at=?, resolved_at=?
                WHERE action_id=?
                """,
                (_json(result), _now(), _now(), action_id),
            )
    return get_owner_action(action_id, database_path=database_path) or {}


def get_owner_action(
    action_id: str, *, database_path: str | Path | None = None
) -> dict[str, object] | None:
    _ensure(database_path)
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM owner_control_actions WHERE action_id=?", (action_id,)
        ).fetchone()
    return _action(row) if row else None


def list_owner_actions(
    *,
    project_id: str | None = None,
    status: str | None = None,
    database_path: str | Path | None = None,
) -> list[dict[str, object]]:
    _ensure(database_path)
    clauses, params = [], []
    if project_id is not None:
        clauses.append("project_id=?")
        params.append(project_id)
    if status:
        clauses.append("status=?")
        params.append(str(status))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with db.connect(database_path) as database:
        rows = database.execute(
            "SELECT * FROM owner_control_actions" + where + " ORDER BY created_at DESC",
            tuple(params),
        ).fetchall()
    return [_action(row) for row in rows]


def resolve_owner_action(
    action_id: str,
    *,
    approved: bool,
    actor: str = "human_owner",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    if actor != "human_owner":
        raise PermissionError("only the Human Owner can approve company actions")
    action = get_owner_action(action_id, database_path=database_path)
    if not action:
        raise KeyError(action_id)
    if action["status"] not in {"pending_approval", "requested"}:
        raise ValueError("owner action is already resolved")
    status = "approved" if approved else "rejected"
    result: dict[str, object] = {"approved": bool(approved), "execution": "not_executed"}
    if approved and not action["requires_approval"]:
        result = _apply_action(
            str(action["action"]),
            action.get("project_id"),
            action.get("payload") if isinstance(action.get("payload"), dict) else {},
            action_id=action_id,
            database_path=database_path,
        )
        status = "applied"
    elif approved:
        result["execution"] = "requires_explicit_external_operator"
    with db.connect(database_path) as database:
        database.execute(
            """
            UPDATE owner_control_actions
            SET status=?, approved_by=?, result_json=?, updated_at=?, resolved_at=?
            WHERE action_id=?
            """,
            (status, actor, _json(result), _now(), _now(), action_id),
        )
    return get_owner_action(action_id, database_path=database_path) or {}


def _opportunity(row) -> ProjectOpportunity:
    keys = set(row.keys())
    values = _load(row["requirements_json"], [])
    values = values if isinstance(values, list) else []
    brief = _load(row["brief_json"], {}) if "brief_json" in keys else {}
    qualification = _load(row["qualification_json"], {}) if "qualification_json" in keys else {}
    return ProjectOpportunity(
        opportunity_id=row["opportunity_id"],
        source=row["source"],
        external_ref=row["external_ref"],
        title=row["title"],
        summary=row["summary"],
        requirements=tuple(str(item)[:2000] for item in values[:100]),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        brief=brief if isinstance(brief, dict) else {},
        qualification=qualification if isinstance(qualification, dict) else {},
        owner_gate_status=str(row["owner_gate_status"]) if "owner_gate_status" in keys else "not_required",
        converted_project_id=row["converted_project_id"] if "converted_project_id" in keys else None,
        converted_at=row["converted_at"] if "converted_at" in keys else None,
        last_action=str(row["last_action"]) if "last_action" in keys else "",
    )


def create_project_opportunity(
    source: str,
    title: str,
    *,
    summary: str = "",
    requirements: list[str] | tuple[str, ...] = (),
    external_ref: str | None = None,
    status: str = "inbox",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    source, title = str(source).strip()[:128], str(title).strip()[:500]
    if not source or not title:
        raise ValueError("opportunity source and title are required")
    opportunity_id, now = str(uuid4()), _now()
    with db.connect(database_path) as database:
        database.execute(
            """
            INSERT INTO project_opportunities(
                opportunity_id, source, external_ref, title, summary,
                requirements_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_ref) DO UPDATE SET
                title=excluded.title, summary=excluded.summary,
                requirements_json=excluded.requirements_json,
                status=excluded.status, updated_at=excluded.updated_at
            """,
            (
                opportunity_id,
                source,
                external_ref,
                title,
                str(summary or "")[:10000],
                json.dumps([str(item)[:2000] for item in requirements[:100]], ensure_ascii=False),
                str(status or "inbox")[:64],
                now,
                now,
            ),
        )
        row = database.execute(
            "SELECT * FROM project_opportunities WHERE source=? AND external_ref IS ?",
            (source, external_ref),
        ).fetchone()
    return _opportunity(row).as_dict()


def update_project_opportunity(
    opportunity_id: str,
    *,
    status: str | None = None,
    brief: dict[str, object] | None = None,
    qualification: dict[str, object] | None = None,
    owner_gate_status: str | None = None,
    converted_project_id: str | None = None,
    converted_at: str | None = None,
    last_action: str | None = None,
    database_path: str | Path | None = None,
) -> dict[str, object]:
    """Update durable intake state; omitted fields remain unchanged."""
    _ensure(database_path)
    updates: list[str] = []
    params: list[object] = []
    if status is not None:
        updates.append("status=?")
        params.append(str(status)[:64])
    if brief is not None:
        updates.append("brief_json=?")
        params.append(_json(_clean_payload(brief)))
    if qualification is not None:
        updates.append("qualification_json=?")
        params.append(_json(_clean_payload(qualification)))
    if owner_gate_status is not None:
        updates.append("owner_gate_status=?")
        params.append(str(owner_gate_status)[:64])
    if converted_project_id is not None:
        updates.append("converted_project_id=?")
        params.append(str(converted_project_id)[:128])
    if converted_at is not None:
        updates.append("converted_at=?")
        params.append(str(converted_at)[:64])
    if last_action is not None:
        updates.append("last_action=?")
        params.append(str(last_action)[:128])
    if not updates:
        current = get_project_opportunity(opportunity_id, database_path=database_path)
        if current is None:
            raise KeyError(opportunity_id)
        return current
    updates.append("updated_at=?")
    params.append(_now())
    params.append(opportunity_id)
    with db.connect(database_path) as database:
        result = database.execute(
            f"UPDATE project_opportunities SET {', '.join(updates)} WHERE opportunity_id=?",
            tuple(params),
        )
        if result.rowcount == 0:
            raise KeyError(opportunity_id)
    return get_project_opportunity(opportunity_id, database_path=database_path) or {}


_OPPORTUNITY_TRANSITIONS = {
    "NEW": {"ANALYZING", "NEEDS_CLARIFICATION", "QUALIFIED", "REJECTED", "WAITING_OWNER"},
    "ANALYZING": {"NEEDS_CLARIFICATION", "QUALIFIED", "REJECTED", "WAITING_OWNER"},
    "NEEDS_CLARIFICATION": {"ANALYZING", "QUALIFIED", "REJECTED"},
    "QUALIFIED": {"CONVERTED_TO_PROJECT", "WAITING_OWNER"},
    "WAITING_OWNER": {"QUALIFIED", "REJECTED"},
    "REJECTED": set(),
    "CONVERTED_TO_PROJECT": {"CONVERTED_TO_PROJECT"},
}


def transition_project_opportunity(
    opportunity_id: str,
    target_status: str,
    *,
    owner_gate_status: str | None = None,
    last_action: str | None = None,
    database_path: str | Path | None = None,
) -> dict[str, object]:
    item = get_project_opportunity(opportunity_id, database_path=database_path)
    if not item:
        raise KeyError(opportunity_id)
    target = str(target_status).strip().upper()
    if target not in _OPPORTUNITY_TRANSITIONS:
        raise ValueError(f"Unsupported opportunity status: {target}")
    current = str(item.get("status") or "NEW").upper()
    if current == "INBOX":
        current = "NEW"
    if target != current and target not in _OPPORTUNITY_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid opportunity transition: {current} -> {target}")
    return update_project_opportunity(
        opportunity_id, status=target, owner_gate_status=owner_gate_status,
        last_action=last_action, database_path=database_path,
    )


def get_project_opportunity(
    opportunity_id: str, *, database_path: str | Path | None = None
) -> dict[str, object] | None:
    _ensure(database_path)
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM project_opportunities WHERE opportunity_id=?", (opportunity_id,)
        ).fetchone()
    return _opportunity(row).as_dict() if row else None


def list_project_opportunities(
    *, source: str | None = None, status: str | None = None, database_path: str | Path | None = None
) -> list[dict[str, object]]:
    _ensure(database_path)
    with db.connect(database_path) as database:
        rows = database.execute(
            """
            SELECT * FROM project_opportunities
            WHERE (? IS NULL OR source=?)
              AND (? IS NULL OR status=?)
            ORDER BY updated_at DESC
            """,
            (source, source, status, status),
        ).fetchall()
    return [_opportunity(row).as_dict() for row in rows]

