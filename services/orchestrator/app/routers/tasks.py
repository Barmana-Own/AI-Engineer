from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, status

from app.clients import request_json
from app.config import settings
from app.schemas import (
    ChatTaskRequest,
    FileWriteTaskRequest,
    TerminalTaskRequest,
    TerminalTaskResponse,
)

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.post("/chat")
async def chat_task(request: ChatTaskRequest) -> Any:
    payload = request.model_dump(exclude_none=True)

    return await request_json(
        "POST",
        f"{settings.model_gateway_url}/v1/chat/completions",
        json=payload,
        timeout_seconds=settings.request_timeout_seconds,
    )


@router.get("/files/list")
async def list_files(path: str = ".") -> Any:
    encoded = quote(path, safe="")

    return await request_json(
        "GET",
        f"{settings.local_agent_url}/files/list?path={encoded}",
    )


@router.get("/files/read")
async def read_file(path: str) -> Any:
    encoded = quote(path, safe="")

    return await request_json(
        "GET",
        f"{settings.local_agent_url}/files/read?path={encoded}",
    )


@router.post("/files/write")
async def write_file(request: FileWriteTaskRequest) -> Any:
    return await request_json(
        "POST",
        f"{settings.local_agent_url}/files/write",
        json=request.model_dump(),
    )


@router.post(
    "/terminal",
    response_model=TerminalTaskResponse,
)
async def terminal_task(
    request: TerminalTaskRequest,
) -> TerminalTaskResponse:
    preview_payload = {
        "command": request.command,
        "cwd": request.cwd,
        "shell": request.shell,
    }

    preview = await request_json(
        "POST",
        f"{settings.local_agent_url}/terminal/preview",
        json=preview_payload,
    )

    risk = preview.get("risk")

    if risk == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Command is blocked by the Local Agent.",
                "preview": preview,
            },
        )

    if risk == "approval_required" and not request.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Explicit approval is required.",
                "preview": preview,
            },
        )

    run_payload = request.model_dump()

    result = await request_json(
        "POST",
        f"{settings.local_agent_url}/terminal/run",
        json=run_payload,
        timeout_seconds=request.timeout_seconds
        or settings.request_timeout_seconds,
    )

    return TerminalTaskResponse(
        preview=preview,
        result=result,
    )