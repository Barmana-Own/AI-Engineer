from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app import db
from app.coordination.roles import get_role_contract, resolve_role
from app.coordination.models import WritePermission

from .models import (
    AgentProfile,
    Department,
    EmployeeStatus,
    ProjectOrganization,
    ProjectOrganizationPlan,
    ProjectTeamMember,
)

_ROLE_DEPARTMENTS: dict[str, Department] = {
    "company_director": Department.EXECUTIVE,
    "project_manager": Department.PRODUCT,
    "requirements": Department.PRODUCT,
    "sales": Department.PRODUCT,
    "supervisor": Department.ENGINEERING,
    "engineering_manager": Department.ENGINEERING,
    "planner": Department.PRODUCT,
    "architect": Department.ENGINEERING,
    "researcher": Department.RESEARCH,
    "backend": Department.ENGINEERING,
    "frontend": Department.ENGINEERING,
    "implementer": Department.ENGINEERING,
    "integration": Department.ENGINEERING,
    "tester": Department.QUALITY,
    "debugger": Department.ENGINEERING,
    "reviewer": Department.QUALITY,
    "security": Department.SECURITY,
    "docs": Department.DOCUMENTATION,
    "release_verifier": Department.OPERATIONS,
    "incident_manager": Department.OPERATIONS,
    "operations": Department.OPERATIONS,
}


def _bounded_strings(values: Iterable[str] | None, limit: int = 100) -> tuple[str, ...]:
    result: list[str] = []
    for value in values or ():
        text = str(value).strip()
        if text and text not in result:
            result.append(text[:500])
        if len(result) >= limit:
            break
    return tuple(result)


def _json_list(value: str | None) -> tuple[str, ...]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return ()
    if not isinstance(parsed, list):
        return ()
    return _bounded_strings(parsed)


def _json_dump(values: Iterable[str] | None) -> str:
    return json.dumps(list(_bounded_strings(values)), ensure_ascii=False)


def _coerce_department(value: Department | str) -> Department:
    if isinstance(value, Department):
        return value
    try:
        return Department(str(value).strip().upper())
    except ValueError as exc:
        raise ValueError(f"Unsupported department: {value}") from exc


def _coerce_status(value: EmployeeStatus | str) -> EmployeeStatus:
    if isinstance(value, EmployeeStatus):
        return value
    try:
        return EmployeeStatus(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported employee status: {value}") from exc


def _row_to_profile(row: Any) -> AgentProfile:
    return AgentProfile(
        agent_id=str(row["agent_id"]),
        role=str(row["role"]),
        display_name=str(row["display_name"]),
        department=_coerce_department(row["department"]),
        capabilities=_json_list(row["capabilities_json"]),
        specializations=_json_list(row["specializations_json"]),
        allowed_tools=_json_list(row["allowed_tools_json"]),
        write_permission=str(row["write_permission"]),
        model_profile=str(row["model_profile"]),
        status=_coerce_status(row["status"]),
        active_project=row["active_project"],
        current_tasks=_json_list(row["current_tasks_json"]),
        experience_summary=str(row["experience_summary"] or ""),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _row_to_member(row: Any) -> ProjectTeamMember:
    return ProjectTeamMember(
        agent_id=str(row["agent_id"]),
        role=str(row["role"]),
        department=_coerce_department(row["department"]),
        status=_coerce_status(row["status"]),
        is_lead=bool(row["is_lead"]),
        display_name=row["display_name"] if "display_name" in row.keys() else None,
    )


def _agent_id_for_role(role: str) -> str:
    return f"employee-{role.replace('_', '-')}"


def ensure_employee(
    role: str,
    *,
    agent_id: str | None = None,
    display_name: str | None = None,
    department: Department | str | None = None,
    capabilities: Iterable[str] | None = None,
    specializations: Iterable[str] | None = None,
    allowed_tools: Iterable[str] | None = None,
    write_permission: str | WritePermission | None = None,
    model_profile: str | None = None,
    status: EmployeeStatus | str = EmployeeStatus.AVAILABLE,
    active_project: str | None = None,
    current_tasks: Iterable[str] | None = None,
    experience_summary: str = "",
    database_path: str | Path | None = None,
) -> AgentProfile:
    resolved_role = resolve_role(role)
    contract = get_role_contract(resolved_role)
    resolved_department = _coerce_department(
        department or _ROLE_DEPARTMENTS.get(resolved_role, Department.ENGINEERING)
    )
    resolved_agent_id = agent_id or _agent_id_for_role(resolved_role)
    resolved_name = display_name or contract.name
    permission = write_permission or contract.write_permission
    if isinstance(permission, WritePermission):
        permission = permission.value
    now = db.utc_now()
    db.initialize_database(database_path)
    with db.connect(database_path) as database:
        existing = database.execute(
            "SELECT created_at FROM agent_profiles WHERE agent_id = ?",
            (resolved_agent_id,),
        ).fetchone()
        created_at = str(existing["created_at"]) if existing else now
        database.execute(
            """
            INSERT INTO agent_profiles(
                agent_id, role, display_name, department, capabilities_json,
                specializations_json, allowed_tools_json, write_permission,
                model_profile, status, active_project, current_tasks_json,
                experience_summary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                role=excluded.role,
                display_name=excluded.display_name,
                department=excluded.department,
                capabilities_json=excluded.capabilities_json,
                specializations_json=excluded.specializations_json,
                allowed_tools_json=excluded.allowed_tools_json,
                write_permission=excluded.write_permission,
                model_profile=excluded.model_profile,
                status=excluded.status,
                active_project=excluded.active_project,
                current_tasks_json=excluded.current_tasks_json,
                experience_summary=excluded.experience_summary,
                updated_at=excluded.updated_at
            """,
            (
                resolved_agent_id,
                resolved_role,
                resolved_name,
                resolved_department.value,
                _json_dump(capabilities if capabilities is not None else contract.capabilities),
                _json_dump(specializations),
                _json_dump(allowed_tools if allowed_tools is not None else contract.allowed_tools),
                str(permission),
                model_profile or contract.default_model_profile,
                _coerce_status(status).value,
                active_project,
                _json_dump(current_tasks),
                str(experience_summary or "")[:4000],
                created_at,
                now,
            ),
        )
        row = database.execute(
            "SELECT * FROM agent_profiles WHERE agent_id = ?", (resolved_agent_id,)
        ).fetchone()
    return _row_to_profile(row)


def get_employee(
    agent_id: str, *, database_path: str | Path | None = None
) -> AgentProfile | None:
    db.initialize_database(database_path)
    with db.connect(database_path) as database:
        row = database.execute(
            "SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)
        ).fetchone()
    return _row_to_profile(row) if row else None


def list_employees(
    *,
    role: str | None = None,
    department: Department | str | None = None,
    status: EmployeeStatus | str | None = None,
    database_path: str | Path | None = None,
) -> list[AgentProfile]:
    db.initialize_database(database_path)
    clauses: list[str] = []
    params: list[str] = []
    if role:
        clauses.append("role = ?")
        params.append(resolve_role(role))
    if department:
        clauses.append("department = ?")
        params.append(_coerce_department(department).value)
    if status:
        clauses.append("status = ?")
        params.append(_coerce_status(status).value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with db.connect(database_path) as database:
        rows = database.execute(
            f"SELECT * FROM agent_profiles{where} ORDER BY role, agent_id",
            tuple(params),
        ).fetchall()
    return [_row_to_profile(row) for row in rows]


def update_employee_status(
    agent_id: str,
    status: EmployeeStatus | str,
    *,
    active_project: str | None = None,
    current_tasks: Iterable[str] | None = None,
    database_path: str | Path | None = None,
) -> AgentProfile:
    resolved_status = _coerce_status(status)
    db.initialize_database(database_path)
    now = db.utc_now()
    with db.connect(database_path) as database:
        cursor = database.execute(
            """
            UPDATE agent_profiles
            SET status = ?, active_project = ?, current_tasks_json = ?, updated_at = ?
            WHERE agent_id = ?
            """,
            (
                resolved_status.value,
                active_project,
                _json_dump(current_tasks),
                now,
                agent_id,
            ),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"Employee profile not found: {agent_id}")
        row = database.execute(
            "SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)
        ).fetchone()
    return _row_to_profile(row)


def save_project_organization(
    plan: ProjectOrganizationPlan,
    *,
    database_path: str | Path | None = None,
) -> ProjectOrganization:
    db.initialize_database(database_path)
    now = db.utc_now()
    with db.connect(database_path) as database:
        project = database.execute(
            "SELECT * FROM projects WHERE id = ?", (plan.project_id,)
        ).fetchone()
        if not project:
            raise KeyError(f"Project not found: {plan.project_id}")
        for member in plan.members:
            ensure_employee(
                member.role,
                agent_id=member.agent_id,
                display_name=member.display_name,
                department=member.department,
                status=member.status,
                active_project=plan.project_id,
                database_path=database_path,
            )
        database.execute(
            """
            UPDATE projects SET project_manager_id = ?, engineering_manager_id = ?,
                departments_json = ?, phase = ?, priority = ?, team_state = ?,
                updated_at = ? WHERE id = ?
            """,
            (
                plan.project_manager_id,
                plan.engineering_manager_id,
                json.dumps([department.value for department in plan.departments]),
                plan.phase,
                max(0, min(100, int(plan.priority))),
                plan.team_state,
                now,
                plan.project_id,
            ),
        )
        database.execute(
            "DELETE FROM project_team_members WHERE project_id = ?",
            (plan.project_id,),
        )
        for member in plan.members:
            database.execute(
                """
                INSERT INTO project_team_members(
                    project_id, agent_id, role, department, status, is_lead,
                    assigned_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.project_id,
                    member.agent_id,
                    member.role,
                    member.department.value,
                    member.status.value,
                    int(member.is_lead),
                    now,
                    now,
                ),
            )
        project = database.execute(
            "SELECT * FROM projects WHERE id = ?", (plan.project_id,)
        ).fetchone()
        rows = database.execute(
            """
            SELECT tm.*, ap.display_name
            FROM project_team_members tm
            JOIN agent_profiles ap ON ap.agent_id = tm.agent_id
            WHERE tm.project_id = ?
            ORDER BY tm.is_lead DESC, tm.role
            """,
            (plan.project_id,),
        ).fetchall()
    return ProjectOrganization(
        project=db._row_to_project(project),
        members=tuple(_row_to_member(row) for row in rows),
    )


def list_project_team(
    project_id: str, *, database_path: str | Path | None = None
) -> list[ProjectTeamMember]:
    db.initialize_database(database_path)
    with db.connect(database_path) as database:
        rows = database.execute(
            """
            SELECT tm.*, ap.display_name
            FROM project_team_members tm
            JOIN agent_profiles ap ON ap.agent_id = tm.agent_id
            WHERE tm.project_id = ?
            ORDER BY tm.is_lead DESC, tm.role
            """,
            (project_id,),
        ).fetchall()
    return [_row_to_member(row) for row in rows]


def get_project_organization(
    project_id: str, *, database_path: str | Path | None = None
) -> ProjectOrganization | None:
    db.initialize_database(database_path)
    with db.connect(database_path) as database:
        project = database.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if not project:
        return None
    return ProjectOrganization(
        project=db._row_to_project(project),
        members=tuple(list_project_team(project_id, database_path=database_path)),
    )
