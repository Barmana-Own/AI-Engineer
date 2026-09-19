from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.db import create_project, get_project, list_projects
from app.schemas import ProjectCreateRequest, ProjectResponse
from app.organization.director import CompanyDirector

router = APIRouter(prefix="/v1/projects", tags=["projects"])

WORKSPACE_ROOT = Path(settings.workspace_root).expanduser().resolve()
SELF_WORKSPACE_NAME = settings.self_workspace_name
SELF_WORKSPACE_ROOT = Path(settings.self_workspace_root).expanduser().resolve()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\u0600-\u06ff-]+", "-", value, flags=re.UNICODE)
    value = value.strip("-_")
    return value or "project"


def normalize_workspace(value: str) -> str:
    supplied_text = value.replace("\\", "/").strip().strip("/")
    if supplied_text.casefold() == SELF_WORKSPACE_NAME:
        if not SELF_WORKSPACE_ROOT.is_dir():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI Engineer repository is not available.",
            )
        return SELF_WORKSPACE_NAME

    supplied = Path(supplied_text)

    if supplied.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace must be relative to the configured workspace root.",
        )

    resolved = (WORKSPACE_ROOT / supplied).resolve()

    try:
        relative = resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace escapes the allowed root.",
        ) from exc

    resolved.mkdir(parents=True, exist_ok=True)
    return relative.as_posix()


@router.get("", response_model=list[ProjectResponse])
def projects_list() -> list[ProjectResponse]:
    return [ProjectResponse(**project) for project in list_projects()]


@router.get("/{project_id}", response_model=ProjectResponse)
def project_get(project_id: str) -> ProjectResponse:
    project = get_project(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    # Form the smallest useful persistent team immediately; the existing
    # coordination Supervisor still owns technical task execution.
    try:
        CompanyDirector().organize_project(project["id"], request.name.strip())
        project = get_project(project["id"]) or project
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project was created but its organization could not be formed.",
        ) from exc
    return ProjectResponse(**project)


@router.post("", response_model=ProjectResponse)
def project_create(request: ProjectCreateRequest) -> ProjectResponse:
    workspace = normalize_workspace(
        request.workspace or slugify(request.name)
    )

    try:
        project = create_project(
            name=request.name.strip(),
            workspace=workspace,
        )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project already uses this workspace.",
            ) from exc
        raise

    return ProjectResponse(**project)
