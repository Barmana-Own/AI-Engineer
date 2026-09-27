from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.db import get_project
from app.coordination import project_management as management
from app.schemas import (
    MilestoneCreateRequest,
    ProjectPhaseTransitionRequest,
    QualityGateRequest,
    QueueCompleteRequest,
    QueueCreateRequest,
    RiskCreateRequest,
)

router = APIRouter(prefix="/v1", tags=["project-management"])


def _project_or_404(project_id: str) -> None:
    if not get_project(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/projects/{project_id}/management")
def project_management(project_id: str) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return {
            "project": management.get_project_state(project_id),
            "sync": management.sync_project(project_id),
            "lifecycle": management.list_lifecycle_events(project_id),
            "milestones": management.list_milestones(project_id),
            "risks": management.list_risks(project_id),
            "quality_gates": management.list_quality_gates(project_id),
            "work_queue": management.list_work_queue(project_id=project_id),
        }
    except (KeyError, ValueError) as exc:
        raise _bad_request(exc) from exc


@router.post("/projects/{project_id}/phase")
def project_phase(project_id: str, request: ProjectPhaseTransitionRequest) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return management.transition_project_phase(
            project_id,
            request.phase,
            actor_role=request.actor_role,
            evidence=request.evidence,
            reason=request.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/projects/{project_id}/lifecycle")
def project_lifecycle(project_id: str) -> dict[str, object]:
    _project_or_404(project_id)
    return {"project_id": project_id, "events": management.list_lifecycle_events(project_id)}


@router.post("/projects/{project_id}/quality-gates")
def quality_gate(project_id: str, request: QualityGateRequest) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return management.set_quality_gate(
            project_id,
            request.gate_name,
            status=request.status,
            required=request.required,
            evidence=request.evidence,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/projects/{project_id}/quality-gates")
def quality_gates(project_id: str) -> dict[str, object]:
    _project_or_404(project_id)
    return {"project_id": project_id, "gates": management.list_quality_gates(project_id)}


@router.post("/projects/{project_id}/milestones")
def milestone_create(project_id: str, request: MilestoneCreateRequest) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return management.create_milestone(
            project_id,
            request.title,
            description=request.description,
            state=request.state,
            due_at=request.due_at,
            deliverables=request.deliverables,
            dependencies=request.dependencies,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/projects/{project_id}/milestones")
def milestones(project_id: str) -> dict[str, object]:
    _project_or_404(project_id)
    return {"project_id": project_id, "milestones": management.list_milestones(project_id)}


@router.post("/projects/{project_id}/risks")
def risk_create(project_id: str, request: RiskCreateRequest) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return management.create_risk(
            project_id,
            request.title,
            severity=request.severity,
            status=request.status,
            mitigation=request.mitigation,
            owner=request.owner,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/projects/{project_id}/risks")
def risks(project_id: str, status_filter: str | None = Query(default=None, alias="status", max_length=32)) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return {"project_id": project_id, "risks": management.list_risks(project_id, status=status_filter)}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/work-queues")
def work_queues(
    agent_id: str | None = Query(default=None, max_length=128),
    project_id: str | None = Query(default=None, max_length=128),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
) -> dict[str, object]:
    return {
        "items": management.list_work_queue(
            agent_id=agent_id,
            project_id=project_id,
            status=status_filter,
        )
    }


@router.post("/projects/{project_id}/work-queues")
def work_queue_create(project_id: str, request: QueueCreateRequest) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return management.enqueue_work(
            request.agent_id,
            project_id,
            request.item_type,
            request.item_ref,
            task_id=request.task_id,
            priority=request.priority,
            blocked_by=request.blocked_by,
            available_at=request.available_at,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/work-queues/{queue_id}/claim")
def work_queue_claim(queue_id: str, agent_id: str = Query(..., min_length=1, max_length=128)) -> dict[str, object]:
    try:
        item = management.claim_next_work(agent_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if not item or item["queue_id"] != queue_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Queue item is unavailable.")
    return item


@router.post("/work-queues/{queue_id}/complete")
def work_queue_complete(queue_id: str, request: QueueCompleteRequest) -> dict[str, object]:
    try:
        return management.complete_work(queue_id, status=request.status)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/scheduler/ready-tasks")
def schedule_ready_tasks(
    project_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    try:
        return {"items": management.schedule_ready_tasks(project_id=project_id, limit=limit)}
    except (KeyError, ValueError) as exc:
        raise _bad_request(exc) from exc


@router.get("/blackboard")
def blackboard(project_id: str | None = Query(default=None, max_length=128)) -> dict[str, object]:
    if project_id:
        _project_or_404(project_id)
    return management.blackboard(project_id=project_id)


@router.get("/projects/{project_id}/sync")
def project_sync(project_id: str) -> dict[str, object]:
    _project_or_404(project_id)
    try:
        return management.sync_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
