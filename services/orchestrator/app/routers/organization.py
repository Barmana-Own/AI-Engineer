from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.db import get_project
from app.organization.director import CompanyDirector
from app.organization.models import Department, EmployeeStatus, ProjectComplexity
from app.organization.store import (
    get_employee,
    get_project_organization,
    get_project_team_plan,
    list_employees,
    list_project_team,
    update_employee_status,
)
from app.schemas import (
    EmployeeProfileResponse,
    EmployeeStatusRequest,
    OrganizationPlanRequest,
)

router = APIRouter(prefix="/v1/organization", tags=["organization"])


@router.get("/departments")
def departments() -> dict[str, list[str]]:
    return {"departments": [department.value for department in Department]}


@router.get("/employees", response_model=list[EmployeeProfileResponse])
def employees(
    role: str | None = Query(default=None, max_length=64),
    department: str | None = Query(default=None, max_length=32),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
) -> list[EmployeeProfileResponse]:
    try:
        profiles = list_employees(role=role, department=department, status=status_filter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [EmployeeProfileResponse(**profile.as_dict()) for profile in profiles]


@router.get("/employees/{agent_id}", response_model=EmployeeProfileResponse)
def employee(agent_id: str) -> EmployeeProfileResponse:
    profile = get_employee(agent_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found.")
    return EmployeeProfileResponse(**profile.as_dict())


@router.post("/employees/{agent_id}/status", response_model=EmployeeProfileResponse)
def employee_status(agent_id: str, request: EmployeeStatusRequest) -> EmployeeProfileResponse:
    try:
        profile = update_employee_status(
            agent_id,
            EmployeeStatus(request.status),
            active_project=request.active_project,
            current_tasks=request.current_tasks,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EmployeeProfileResponse(**profile.as_dict())


@router.post("/projects/{project_id}/organize")
def organize_project(project_id: str, request: OrganizationPlanRequest) -> dict[str, object]:
    if not get_project(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        plan, organization = CompanyDirector().organize_project(
            project_id,
            request.objective,
            complexity=(
                ProjectComplexity(request.complexity) if request.complexity else None
            ),
            technologies=request.technologies,
            required_skills=request.required_skills,
            risks=request.risks,
            deliverables=request.deliverables,
            priority=request.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"plan": plan.as_dict(), "organization": organization.as_dict()}


@router.get("/projects/{project_id}/team")
def project_team(project_id: str) -> dict[str, object]:
    if not get_project(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return {"project_id": project_id, "members": [member.as_dict() for member in list_project_team(project_id)]}


@router.get("/projects/{project_id}/team-plan")
def project_team_plan(project_id: str) -> dict[str, object]:
    if not get_project(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    plan = get_project_team_plan(project_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution team plan not found.")
    return plan

@router.get("/projects/{project_id}/report")
def project_report(project_id: str) -> dict[str, object]:
    try:
        return CompanyDirector().executive_report(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
