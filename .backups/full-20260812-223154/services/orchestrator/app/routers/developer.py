from fastapi import APIRouter, HTTPException, status

from app.clients import request_json
from app.config import settings
from app.db import get_project
from app.schemas import (
    GitCheckpointRequest,
    GitDiffRequest,
    GitRollbackRequest,
    ManagedProcessStartRequest,
    ManagedProcessStopRequest,
)

router = APIRouter(prefix="/v1/developer", tags=["developer"])


def project_workspace(project_id: str) -> str:
    project = get_project(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return project["workspace"]


@router.get("/projects/{project_id}/git/status")
async def git_status(project_id: str) -> dict:
    return await request_json(
        "POST",
        f"{settings.local_agent_url}/git/status",
        json={"project_path": project_workspace(project_id)},
    )


@router.post("/projects/{project_id}/git/checkpoint")
async def git_checkpoint(
    project_id: str,
    request: GitCheckpointRequest,
) -> dict:
    return await request_json(
        "POST",
        f"{settings.local_agent_url}/git/checkpoint",
        json={
            "project_path": project_workspace(project_id),
            **request.model_dump(),
        },
    )


@router.post("/projects/{project_id}/git/diff")
async def git_diff(
    project_id: str,
    request: GitDiffRequest,
) -> dict:
    return await request_json(
        "POST",
        f"{settings.local_agent_url}/git/diff",
        json={
            "project_path": project_workspace(project_id),
            **request.model_dump(),
        },
    )


@router.post("/projects/{project_id}/git/rollback")
async def git_rollback(
    project_id: str,
    request: GitRollbackRequest,
) -> dict:
    return await request_json(
        "POST",
        f"{settings.local_agent_url}/git/rollback",
        json={
            "project_path": project_workspace(project_id),
            **request.model_dump(),
        },
    )


@router.get("/processes")
async def processes_list() -> list[dict]:
    return await request_json(
        "GET",
        f"{settings.local_agent_url}/processes",
    )


@router.post("/projects/{project_id}/processes/start")
async def process_start(
    project_id: str,
    request: ManagedProcessStartRequest,
) -> dict:
    workspace = project_workspace(project_id)
    relative_cwd = request.cwd.strip().replace("\\", "/")
    cwd = (
        workspace
        if relative_cwd in {"", "."}
        else f"{workspace.rstrip('/')}/{relative_cwd.lstrip('/')}"
    )

    return await request_json(
        "POST",
        f"{settings.local_agent_url}/processes/start",
        json={
            **request.model_dump(),
            "cwd": cwd,
        },
    )


@router.post("/processes/stop")
async def process_stop(
    request: ManagedProcessStopRequest,
) -> dict:
    return await request_json(
        "POST",
        f"{settings.local_agent_url}/processes/stop",
        json=request.model_dump(),
    )