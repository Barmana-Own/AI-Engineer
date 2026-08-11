from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.agent_service import run_agent_task
from app.db import (
    create_task,
    get_project,
    get_task,
    list_tasks,
    update_task,
)
from app.schemas import (
    AgentApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskResponse,
)

router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.get("/tasks", response_model=list[AgentTaskResponse])
def tasks_list(project_id: str | None = None) -> list[AgentTaskResponse]:
    return [AgentTaskResponse(**task) for task in list_tasks(project_id)]


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
def task_get(task_id: str) -> AgentTaskResponse:
    task = get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return AgentTaskResponse(**task)


@router.post("/tasks", response_model=AgentTaskResponse)
def task_create(
    request: AgentTaskCreateRequest,
    background_tasks: BackgroundTasks,
) -> AgentTaskResponse:
    if not get_project(request.project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    instruction = request.instruction.strip()
    if len(instruction) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Instruction is empty.",
        )

    task = create_task(
        project_id=request.project_id,
        instruction=instruction,
    )
    background_tasks.add_task(run_agent_task, task["id"])
    return AgentTaskResponse(**task)


@router.post(
    "/tasks/{task_id}/approval",
    response_model=AgentTaskResponse,
)
def task_approval(
    task_id: str,
    request: AgentApprovalRequest,
    background_tasks: BackgroundTasks,
) -> AgentTaskResponse:
    task = get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    if task["status"] != "awaiting_approval" or not task.get("pending"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is not awaiting a concrete pending operation.",
        )

    if not request.approved:
        task = update_task(
            task_id,
            status="cancelled",
            pending=None,
            error="User rejected the pending operation.",
        )
        return AgentTaskResponse(**task)

    approved_steps = list(task["approved_steps"])
    step_index = int(task["pending"]["step_index"])
    if step_index not in approved_steps:
        approved_steps.append(step_index)

    # Keep pending intact. run_agent_task must execute this exact approved
    # tool call before asking the model for another action.
    task = update_task(
        task_id,
        status="queued",
        approved_steps=approved_steps,
        error=None,
    )

    background_tasks.add_task(run_agent_task, task_id)
    return AgentTaskResponse(**task)
