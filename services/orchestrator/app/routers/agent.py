from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.agent_service import run_agent_task
from app.autonomy import run_autonomous_cycles
from app.subagents import list_section_subagents, list_subagent_roles
from app.db import (
    create_autonomy_run,
    create_task,
    get_project,
    get_task,
    get_autonomy_run,
    list_tasks,
    list_autonomy_runs,
    list_subagent_handoffs,
    search_memories,
    update_task,
)
from app.schemas import (
    AgentApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskResponse,
    AutonomyRunResponse,
    MemoryResponse,
    SelfImproveRequest,
    SubagentHandoffResponse,
)

router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.get("/subagents")
def subagents_list() -> list[dict[str, object]]:
    """Expose the bounded specialist registry for the UI and monitor."""
    return list_subagent_roles()


@router.get("/subagents/sections")
def section_subagents_list() -> list[dict[str, object]]:
    """Expose one specialist owner for every product section."""
    return list_section_subagents()


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
        mode=request.mode,
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


@router.post(
    "/projects/{project_id}/self-improve",
    response_model=AutonomyRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def self_improve(
    project_id: str,
    request: SelfImproveRequest,
    background_tasks: BackgroundTasks,
) -> AutonomyRunResponse:
    if not get_project(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    active_statuses = {"queued", "planning", "running", "awaiting_approval"}
    if any(
        task.get("mode") == "autonomous" and task.get("status") in active_statuses
        for task in list_tasks(project_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An autonomous self-improvement run is already active for this project.",
        )

    run = create_autonomy_run(
        project_id=project_id,
        goal=request.goal.strip(),
        requested_cycles=request.cycles,
    )
    background_tasks.add_task(run_autonomous_cycles, run["id"])
    return AutonomyRunResponse(**run)


@router.get(
    "/autonomy/runs/{run_id}",
    response_model=AutonomyRunResponse,
)
def autonomy_run_get(run_id: str) -> AutonomyRunResponse:
    run = get_autonomy_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autonomy run not found.",
        )
    return AutonomyRunResponse(**run)


@router.get(
    "/autonomy/runs",
    response_model=list[AutonomyRunResponse],
)
def autonomy_runs_list(
    project_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> list[AutonomyRunResponse]:
    """List recent runs so a supervisor can poll status without run IDs."""
    if project_id and not get_project(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return [
        AutonomyRunResponse(**run)
        for run in list_autonomy_runs(project_id=project_id, limit=limit)
    ]


@router.get(
    "/autonomy/runs/{run_id}/status",
)
def autonomy_run_status(run_id: str) -> dict[str, object]:
    """Return compact run/task status for the supervisor and UI."""
    run = get_autonomy_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autonomy run not found.",
        )

    task_status_counts: dict[str, int] = {}
    for task_id in run.get("task_ids") or []:
        task = get_task(str(task_id))
        if not task:
            continue
        task_status = str(task.get("status") or "unknown")
        task_status_counts[task_status] = task_status_counts.get(task_status, 0) + 1

    # Handoffs are the durable blackboard for section specialists. Include
    # bounded role/status aggregates so the UI and overnight monitor can see
    # specialist progress without downloading every handoff body.
    handoffs = list_subagent_handoffs(run_id, limit=200)
    handoff_status_counts: dict[str, int] = {}
    handoff_role_counts: dict[str, int] = {}
    for handoff in handoffs:
        handoff_status = str(handoff.get("status") or "unknown")
        handoff_role = str(handoff.get("role") or "unknown")
        handoff_status_counts[handoff_status] = (
            handoff_status_counts.get(handoff_status, 0) + 1
        )
        handoff_role_counts[handoff_role] = (
            handoff_role_counts.get(handoff_role, 0) + 1
        )

    return {
        "id": run["id"],
        "project_id": run["project_id"],
        "status": run["status"],
        "requested_cycles": run["requested_cycles"],
        "completed_cycles": run["completed_cycles"],
        "task_count": len(run.get("task_ids") or []),
        "task_status_counts": task_status_counts,
        "error": run.get("error"),
        "updated_at": run["updated_at"],
    }


@router.get(
    "/autonomy/runs/{run_id}/subagents",
    response_model=list[SubagentHandoffResponse],
)
def autonomy_run_subagents(
    run_id: str,
    limit: int = Query(100, ge=1, le=200),
) -> list[SubagentHandoffResponse]:
    """Return the ordered blackboard handoffs produced by a specialist run."""
    if not get_autonomy_run(run_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autonomy run not found.",
        )
    return [
        SubagentHandoffResponse(**handoff)
        for handoff in list_subagent_handoffs(run_id, limit=limit)
    ]


@router.get(
    "/projects/{project_id}/memory",
    response_model=list[MemoryResponse],
)
def project_memory(project_id: str, limit: int = Query(12, ge=1, le=50)) -> list[MemoryResponse]:
    if not get_project(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return [
        MemoryResponse(**memory)
        for memory in search_memories(project_id, limit=limit)
    ]
