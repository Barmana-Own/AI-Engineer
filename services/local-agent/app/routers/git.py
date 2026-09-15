from fastapi import APIRouter

from app.models import (
    GitCheckpointRequest,
    GitDiffRequest,
    GitProjectRequest,
    GitRollbackRequest,
)
from app.services.git_tools import (
    git_checkpoint,
    git_diff,
    git_rollback,
    git_status,
)

router = APIRouter(prefix="/git", tags=["git"])


@router.post("/status")
def status(request: GitProjectRequest) -> dict:
    return git_status(request.project_path)


@router.post("/checkpoint")
def checkpoint(request: GitCheckpointRequest) -> dict:
    return git_checkpoint(
        project_path=request.project_path,
        message=request.message,
        include_untracked=request.include_untracked,
    )


@router.post("/diff")
def diff(request: GitDiffRequest) -> dict:
    return git_diff(
        project_path=request.project_path,
        staged=request.staged,
        base=request.base,
    )


@router.post("/rollback")
def rollback(request: GitRollbackRequest) -> dict:
    return git_rollback(
        project_path=request.project_path,
        commit=request.commit,
        approved=request.approved,
    )