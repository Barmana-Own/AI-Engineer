
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from app import db
from app.memory import MemoryStore
from app.organization.store import ensure_employee, list_employees

INCIDENT_PHASES = (
    "detect",
    "contain",
    "diagnose",
    "repair",
    "verify",
    "postmortem",
    "learn",
    "resolved",
)
_ALLOWED = {
    "detect": {"contain"},
    "contain": {"diagnose"},
    "diagnose": {"repair"},
    "repair": {"verify"},
    "verify": {"postmortem", "repair"},
    "postmortem": {"learn"},
    "learn": {"resolved"},
    "resolved": set(),
}
_SEVERITIES = {"critical", "high", "medium", "low"}
_TEAM_ROLES = (
    "incident_manager",
    "debugger",
    "tester",
    "operations",
    "security",
    "backend",
)
_DATE_COLUMNS = {
    "contain": "contained_at",
    "diagnose": "diagnosed_at",
    "repair": "repaired_at",
    "verify": "verified_at",
    "resolved": "closed_at",
}


def _ensure(path: str | Path | None) -> None:
    db.initialize_database(path)


def _now() -> str:
    return db.utc_now()


def _json(value: object, *, limit: int = 100, chars: int = 4000) -> str:
    values = value if isinstance(value, list) else list(value or ()) if isinstance(value, (tuple, set)) else value
    if isinstance(values, list):
        values = [str(item)[:chars] for item in values[:limit]]
    return json.dumps(values if values is not None else [], ensure_ascii=False, default=str)


def _load(value: object, fallback: object = None) -> object:
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback if fallback is not None else []
    return parsed


def _incident(row) -> dict[str, object]:
    if not row:
        return {}
    return {
        "incident_id": row["incident_id"],
        "project_id": row["project_id"],
        "run_id": row["run_id"],
        "title": row["title"],
        "trigger": row["trigger"],
        "severity": row["severity"],
        "description": row["description"],
        "impact": row["impact"],
        "phase": row["phase"],
        "status": row["status"],
        "created_by": row["created_by"],
        "detected_at": row["detected_at"],
        "contained_at": row["contained_at"],
        "diagnosed_at": row["diagnosed_at"],
        "repaired_at": row["repaired_at"],
        "verified_at": row["verified_at"],
        "closed_at": row["closed_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _event(
    database,
    incident_id: str,
    phase: str,
    status: str,
    actor_role: str,
    details: str = "",
    evidence: Iterable[object] = (),
) -> None:
    database.execute(
        """
        INSERT INTO incident_events(
            event_id, incident_id, phase, status, actor_role, details,
            evidence_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            incident_id,
            phase,
            status,
            str(actor_role)[:128],
            str(details or "")[:4000],
            _json(list(evidence), limit=20, chars=2000),
            _now(),
        ),
    )


def create_incident(
    project_id: str | None,
    title: str,
    trigger: str,
    *,
    severity: str = "critical",
    description: str = "",
    impact: str = "",
    run_id: str | None = None,
    created_by: str = "system",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    clean_title = str(title).strip()
    if not clean_title:
        raise ValueError("incident title is required")
    severity = str(severity).strip().lower()
    if severity not in _SEVERITIES:
        raise ValueError("unsupported incident severity")
    incident_id, now = str(uuid4()), _now()
    with db.connect(database_path) as database:
        if project_id and not database.execute(
            "SELECT 1 FROM projects WHERE id = ?", (project_id,)
        ).fetchone():
            raise KeyError(project_id)
        database.execute(
            """
            INSERT INTO incidents(
                incident_id, project_id, run_id, title, trigger, severity,
                description, impact, phase, status, created_by, detected_at,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'detect', 'open', ?, ?, ?, ?)
            """,
            (
                incident_id,
                project_id,
                run_id,
                clean_title[:500],
                str(trigger).strip()[:256],
                severity,
                str(description or "")[:20000],
                str(impact or "")[:10000],
                str(created_by)[:128],
                now,
                now,
                now,
            ),
        )
        _event(
            database,
            incident_id,
            "detect",
            "open",
            created_by,
            "Incident detected.",
            (trigger,),
        )
    return get_incident(incident_id, database_path=database_path) or {}


def get_incident(
    incident_id: str, *, database_path: str | Path | None = None
) -> dict[str, object] | None:
    _ensure(database_path)
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
    return _incident(row) if row else None


def list_incidents(
    *,
    project_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    database_path: str | Path | None = None,
) -> list[dict[str, object]]:
    _ensure(database_path)
    clauses, params = [], []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if status:
        clauses.append("status = ?")
        params.append(str(status).lower())
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(min(max(int(limit), 1), 200))
    with db.connect(database_path) as database:
        rows = database.execute(
            "SELECT * FROM incidents" + where +
            " ORDER BY updated_at DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    return [_incident(row) for row in rows]


def transition_incident(
    incident_id: str,
    phase: str,
    *,
    actor_role: str = "incident_manager",
    details: str = "",
    evidence: Iterable[object] = (),
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    target = str(phase).strip().lower()
    if target not in INCIDENT_PHASES:
        raise ValueError("unsupported incident phase")
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
        if not row:
            raise KeyError(incident_id)
        old = str(row["phase"])
        if target == old:
            return _incident(row)
        if target not in _ALLOWED.get(old, set()):
            raise ValueError(f"invalid incident transition {old}->{target}")
        now = _now()
        column = _DATE_COLUMNS.get(target)
        status = "resolved" if target == "resolved" else "open"
        if column:
            database.execute(
                f"UPDATE incidents SET phase=?, status=?, {column}=?, updated_at=? WHERE incident_id=?",
                (target, status, now, now, incident_id),
            )
        else:
            database.execute(
                "UPDATE incidents SET phase=?, status=?, updated_at=? WHERE incident_id=?",
                (target, status, now, incident_id),
            )
        _event(database, incident_id, target, status, actor_role, details, evidence)
        updated = database.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
    return _incident(updated)


def list_incident_events(
    incident_id: str, *, database_path: str | Path | None = None
) -> list[dict[str, object]]:
    _ensure(database_path)
    with db.connect(database_path) as database:
        rows = database.execute(
            "SELECT * FROM incident_events WHERE incident_id=? ORDER BY created_at ASC",
            (incident_id,),
        ).fetchall()
    return [
        {
            "event_id": row["event_id"],
            "incident_id": row["incident_id"],
            "phase": row["phase"],
            "status": row["status"],
            "actor_role": row["actor_role"],
            "details": row["details"],
            "evidence": _load(row["evidence_json"], []),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def assign_incident_team(
    incident_id: str,
    *,
    roles: Iterable[str] = _TEAM_ROLES,
    domain: str = "",
    database_path: str | Path | None = None,
) -> list[dict[str, object]]:
    _ensure(database_path)
    incident = get_incident(incident_id, database_path=database_path)
    if not incident:
        raise KeyError(incident_id)
    project_id = incident.get("project_id")
    selected = []
    for role in dict.fromkeys(str(item).strip() for item in roles if str(item).strip()):
        selected.append((role, select_agent_for_role(role, domain=domain, database_path=database_path)))
    now = _now()
    with db.connect(database_path) as database:
        for role, agent in selected:
            database.execute(
                """
                INSERT INTO incident_team_members(
                    incident_id, agent_id, role, status, assigned_at, updated_at
                ) VALUES (?, ?, ?, 'assigned', ?, ?)
                ON CONFLICT(incident_id, agent_id) DO UPDATE SET
                    role=excluded.role, status='assigned', updated_at=excluded.updated_at
                """,
                (incident_id, agent["agent_id"], role, now, now),
            )
    return list_incident_team(incident_id, database_path=database_path)


def list_incident_team(
    incident_id: str, *, database_path: str | Path | None = None
) -> list[dict[str, object]]:
    _ensure(database_path)
    with db.connect(database_path) as database:
        rows = database.execute(
            """
            SELECT tm.*, ap.display_name, ap.model_profile, ap.status AS employee_status
            FROM incident_team_members tm
            JOIN agent_profiles ap ON ap.agent_id = tm.agent_id
            WHERE tm.incident_id = ?
            ORDER BY tm.role, tm.agent_id
            """,
            (incident_id,),
        ).fetchall()
    return [
        {
            "incident_id": row["incident_id"],
            "agent_id": row["agent_id"],
            "role": row["role"],
            "status": row["status"],
            "display_name": row["display_name"],
            "model_profile": row["model_profile"],
            "employee_status": row["employee_status"],
            "assigned_at": row["assigned_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def create_postmortem(
    incident_id: str,
    *,
    what_happened: str,
    impact: str = "",
    timeline: Iterable[object] = (),
    root_cause: str = "",
    contributing_factors: Iterable[object] = (),
    repair: str = "",
    verification: Iterable[object] = (),
    prevention_ideas: Iterable[object] = (),
    follow_up_tasks: Iterable[object] = (),
    created_by: str = "incident_manager",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    if not str(what_happened).strip():
        raise ValueError("postmortem what_happened is required")
    incident = get_incident(incident_id, database_path=database_path)
    if not incident:
        raise KeyError(incident_id)
    postmortem_id, now = str(uuid4()), _now()
    with db.connect(database_path) as database:
        database.execute(
            """
            INSERT INTO postmortems(
                postmortem_id, incident_id, project_id, what_happened, impact,
                timeline_json, root_cause, contributing_factors_json, repair,
                verification_json, prevention_ideas_json, follow_up_tasks_json,
                created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET
                what_happened=excluded.what_happened, impact=excluded.impact,
                timeline_json=excluded.timeline_json, root_cause=excluded.root_cause,
                contributing_factors_json=excluded.contributing_factors_json,
                repair=excluded.repair, verification_json=excluded.verification_json,
                prevention_ideas_json=excluded.prevention_ideas_json,
                follow_up_tasks_json=excluded.follow_up_tasks_json,
                updated_at=excluded.updated_at
            """,
            (
                postmortem_id,
                incident_id,
                incident.get("project_id"),
                str(what_happened)[:20000],
                str(impact or "")[:10000],
                _json(list(timeline), limit=100, chars=4000),
                str(root_cause or "")[:10000],
                _json(list(contributing_factors), limit=100, chars=2000),
                str(repair or "")[:10000],
                _json(list(verification), limit=100, chars=2000),
                _json(list(prevention_ideas), limit=100, chars=2000),
                _json(list(follow_up_tasks), limit=100, chars=2000),
                str(created_by)[:128],
                now,
                now,
            ),
        )
        row = database.execute(
            "SELECT * FROM postmortems WHERE incident_id=?", (incident_id,)
        ).fetchone()
    return _postmortem(row)


def _postmortem(row) -> dict[str, object]:
    return {
        "postmortem_id": row["postmortem_id"],
        "incident_id": row["incident_id"],
        "project_id": row["project_id"],
        "what_happened": row["what_happened"],
        "impact": row["impact"],
        "timeline": _load(row["timeline_json"], []),
        "root_cause": row["root_cause"],
        "contributing_factors": _load(row["contributing_factors_json"], []),
        "repair": row["repair"],
        "verification": _load(row["verification_json"], []),
        "prevention_ideas": _load(row["prevention_ideas_json"], []),
        "follow_up_tasks": _load(row["follow_up_tasks_json"], []),
        "lesson_memory_id": row["lesson_memory_id"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_postmortem(
    postmortem_id: str, *, database_path: str | Path | None = None
) -> dict[str, object] | None:
    _ensure(database_path)
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM postmortems WHERE postmortem_id=?", (postmortem_id,)
        ).fetchone()
    return _postmortem(row) if row else None


def list_postmortems(
    *, project_id: str | None = None, database_path: str | Path | None = None
) -> list[dict[str, object]]:
    _ensure(database_path)
    with db.connect(database_path) as database:
        rows = database.execute(
            """
            SELECT * FROM postmortems
            WHERE (? IS NULL OR project_id=?)
            ORDER BY created_at DESC
            """,
            (project_id, project_id),
        ).fetchall()
    return [_postmortem(row) for row in rows]


def promote_postmortem_lesson(
    postmortem_id: str,
    *,
    summary: str,
    evidence: Iterable[dict[str, object]],
    target: str = "validated",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    postmortem = get_postmortem(postmortem_id, database_path=database_path)
    if not postmortem:
        raise KeyError(postmortem_id)
    evidence = list(evidence)
    if not evidence:
        raise ValueError("organizational lesson requires evidence")
    store = MemoryStore(str(database_path) if database_path else None)
    memory = store.create(
        project_id=None,
        memory_type="lesson",
        summary=str(summary).strip()[:4000],
        content={
            "incident_id": postmortem["incident_id"],
            "project_id": postmortem["project_id"],
            "root_cause": postmortem["root_cause"],
            "repair": postmortem["repair"],
            "prevention_ideas": postmortem["prevention_ideas"],
        },
        evidence=evidence,
        source="incident-postmortem",
    )
    memory = store.promote(memory["id"], evidence=evidence, target="validated")
    if target == "trusted":
        memory = store.promote(memory["id"], evidence=evidence, target="trusted")
    with db.connect(database_path) as database:
        database.execute(
            "UPDATE postmortems SET lesson_memory_id=?, updated_at=? WHERE postmortem_id=?",
            (memory["id"], _now(), postmortem_id),
        )
    memory["postmortem_id"] = postmortem_id
    return memory


def list_organizational_lessons(
    *, query: str = "", limit: int = 20, database_path: str | Path | None = None
) -> list[dict[str, object]]:
    return MemoryStore(str(database_path) if database_path else None).retrieve(
        project_id=None, query=query, limit=limit
    )


def record_collaboration_issue(
    issue_type: str,
    signature: str,
    *,
    project_id: str | None = None,
    severity: str = "medium",
    example: str = "",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    issue_type, signature = str(issue_type).strip()[:128], str(signature).strip()[:256]
    if not issue_type or not signature:
        raise ValueError("collaboration issue type and signature are required")
    now = _now()
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM collaboration_quality WHERE project_id IS ? AND signature=?",
            (project_id, signature),
        ).fetchone()
        if row:
            examples = _load(row["examples_json"], [])
            examples = (examples if isinstance(examples, list) else [])[-9:]
            if example:
                examples.append(str(example)[:2000])
            database.execute(
                """
                UPDATE collaboration_quality
                SET occurrences=occurrences+1, severity=?, issue_type=?,
                    examples_json=?, last_seen_at=?, updated_at=?
                WHERE quality_id=?
                """,
                (severity, issue_type, _json(examples, limit=10, chars=2000), now, now, row["quality_id"]),
            )
            row = database.execute(
                "SELECT * FROM collaboration_quality WHERE quality_id=?", (row["quality_id"],)
            ).fetchone()
        else:
            quality_id = str(uuid4())
            database.execute(
                """
                INSERT INTO collaboration_quality(
                    quality_id, project_id, issue_type, signature, severity,
                    occurrences, examples_json, last_seen_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (quality_id, project_id, issue_type, signature, severity, _json([example] if example else []), now, now, now),
            )
            row = database.execute(
                "SELECT * FROM collaboration_quality WHERE quality_id=?", (quality_id,)
            ).fetchone()
    return _quality(row)


def _quality(row) -> dict[str, object]:
    return {
        "quality_id": row["quality_id"],
        "project_id": row["project_id"],
        "issue_type": row["issue_type"],
        "signature": row["signature"],
        "severity": row["severity"],
        "occurrences": int(row["occurrences"]),
        "examples": _load(row["examples_json"], []),
        "last_seen_at": row["last_seen_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_collaboration_quality(
    *, project_id: str | None = None, limit: int = 50, database_path: str | Path | None = None
) -> list[dict[str, object]]:
    _ensure(database_path)
    with db.connect(database_path) as database:
        rows = database.execute(
            """
            SELECT * FROM collaboration_quality
            WHERE (? IS NULL OR project_id=?)
            ORDER BY occurrences DESC, updated_at DESC LIMIT ?
            """,
            (project_id, project_id, min(max(int(limit), 1), 100)),
        ).fetchall()
    return [_quality(row) for row in rows]


def select_agent_for_role(
    role: str,
    *,
    domain: str = "",
    database_path: str | Path | None = None,
) -> dict[str, object]:
    _ensure(database_path)
    profiles = list_employees(role=role, database_path=database_path)
    available = [profile for profile in profiles if profile.status.value in {"available", "idle", "offline"}]
    if not available:
        profile = ensure_employee(role, database_path=database_path)
        available = [profile]
    metrics = MemoryStore(str(database_path) if database_path else None).performance(role=role, domain=domain or None, limit=100)
    metric_by_profile = {str(row.get("model_profile")): row for row in metrics}
    def score(profile) -> tuple[float, float, str]:
        metric = metric_by_profile.get(profile.model_profile, {})
        completed = float(metric.get("tasks_completed") or 0)
        attempted = float(metric.get("tasks_attempted") or 0)
        failures = float(metric.get("test_failures") or 0) + float(metric.get("review_rejections") or 0)
        success_rate = completed / attempted if attempted else 0.0
        return (completed - failures * 0.5 + success_rate, success_rate, profile.agent_id)
    return max(available, key=score).as_dict()

