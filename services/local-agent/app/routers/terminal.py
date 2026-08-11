from fastapi import APIRouter

from app.models import (
    TerminalPreviewRequest,
    TerminalPreviewResponse,
    TerminalRunRequest,
    TerminalRunResponse,
)
from app.services.files import resolve_workspace_path, to_relative_path
from app.services.terminal import classify_command, run_command

router = APIRouter(prefix="/terminal", tags=["terminal"])


@router.post("/preview", response_model=TerminalPreviewResponse)
def preview_command(request: TerminalPreviewRequest) -> TerminalPreviewResponse:
    cwd = resolve_workspace_path(request.cwd, must_exist=True)
    assessment = classify_command(request.command)

    return TerminalPreviewResponse(
        command=request.command,
        cwd=to_relative_path(cwd),
        shell=request.shell,
        risk=assessment.risk,
        requires_approval=assessment.risk == "approval_required",
        reasons=assessment.reasons,
    )


@router.post("/run", response_model=TerminalRunResponse)
def execute_command(request: TerminalRunRequest) -> TerminalRunResponse:
    result = run_command(
        command=request.command,
        cwd=request.cwd,
        shell=request.shell,
        approved=request.approved,
        timeout_seconds=request.timeout_seconds,
    )

    return TerminalRunResponse(**result)