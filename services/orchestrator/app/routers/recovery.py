from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.recovery import (
    LeaseConflictError,
    RecoveryRequiredError,
    acquire_task_lease,
    get_recovery_status,
    heartbeat_task_lease,
    release_task_lease,
    resume_run,
)
from app.schemas import (
    RecoveryHeartbeatRequest,
    RecoveryLeaseRequest,
    RecoveryReleaseRequest,
    RecoveryResumeRequest,
)

router = APIRouter(prefix="/v1/recovery", tags=["recovery"])


@router.get("/status")
def recovery_status(run_id: str | None = Query(default=None, max_length=120)) -> dict:
    return get_recovery_status(run_id)


@router.post("/runs/{run_id}/resume")
def recovery_resume(run_id: str, request: RecoveryResumeRequest | None = None) -> dict:
    try:
        result = resume_run(run_id, verify=bool(request and request.verify))
    except RecoveryRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery run not found.")
    return result


@router.post("/tasks/{task_id}/lease")
def task_lease(task_id: str, request: RecoveryLeaseRequest | None = None) -> dict:
    body = request or RecoveryLeaseRequest()
    try:
        return acquire_task_lease(
            task_id,
            owner_id=body.owner_id,
            run_id=body.run_id,
            ttl_seconds=body.ttl_seconds,
        )
    except LeaseConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RecoveryRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc


@router.post("/tasks/{task_id}/heartbeat")
def task_heartbeat(task_id: str, request: RecoveryHeartbeatRequest) -> dict:
    ok = heartbeat_task_lease(
        task_id, request.lease_token, ttl_seconds=request.ttl_seconds
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Lease is missing or expired.")
    return {"task_id": task_id, "ok": True}


@router.post("/tasks/{task_id}/release")
def task_release(task_id: str, request: RecoveryReleaseRequest) -> dict:
    ok = release_task_lease(task_id, request.lease_token, error=request.error)
    if not ok:
        raise HTTPException(status_code=409, detail="Lease is missing or already released.")
    return {"task_id": task_id, "ok": True}
