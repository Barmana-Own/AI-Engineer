from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from app.config import settings
from app.db import get_project
from app.schemas import (
    ImprovementObserveRequest, ImprovementStartRequest, ImprovementTestsRequest,
    ImprovementReviewRequest, ImprovementInterruptRequest, ImprovementRollbackRequest,
)
from app.self_improvement import SelfImprovementEngine

router = APIRouter(prefix="/v1/self-improvement", tags=["self-improvement"])

def _engine(repo_root: str | None = None) -> SelfImprovementEngine:
    return SelfImprovementEngine(repo_root=repo_root)

@router.get("/limits")
def limits() -> dict[str, object]:
    return {
        "max_changes_per_run": settings.autonomous_max_changes_per_run,
        "max_retries": settings.autonomous_max_retries,
        "max_runtime_seconds": settings.autonomous_max_runtime_seconds,
        "max_files_changed": settings.autonomous_max_files_changed,
        "allowed_project_roots": settings.autonomous_allowed_project_roots,
        "allowed_commands": settings.autonomous_allowed_commands,
        "rollback_enabled": settings.autonomous_rollback_enabled,
        "automatic_remote_push": False,
    }

@router.post("/observe")
def observe(payload: ImprovementObserveRequest) -> dict[str, object]:
    if not get_project(payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return _engine(payload.repo_root).observe_and_propose(payload.project_id, repo_root=payload.repo_root)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/candidates")
def candidates(project_id: str | None = None, status: str | None = None,
               limit: int = Query(default=50, ge=1, le=100)) -> dict[str, object]:
    statuses = [status] if status else None
    return {"candidates": SelfImprovementEngine().list_candidates(project_id, statuses=statuses, limit=limit)}

@router.post("/candidates/{candidate_id}/start")
def start(candidate_id: str, payload: ImprovementStartRequest) -> dict[str, object]:
    try:
        return SelfImprovementEngine().start_cycle(candidate_id, expected_files=payload.expected_files, expected_tests=payload.expected_tests)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Candidate not found") from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post("/cycles/{cycle_id}/checkpoint")
def checkpoint(cycle_id: str) -> dict[str, object]:
    try:
        return SelfImprovementEngine().checkpoint(cycle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Cycle not found") from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post("/cycles/{cycle_id}/tests")
def tests(cycle_id: str, payload: ImprovementTestsRequest) -> dict[str, object]:
    try:
        passed = payload.passed if payload.passed is not None else (not payload.regressions and bool(payload.tests_after))
        return SelfImprovementEngine().record_tests(
            cycle_id,
            phase="after",
            results={"tests_before": payload.tests_before, "tests_after": payload.tests_after, "regressions": payload.regressions},
            passed=passed,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Cycle not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post("/cycles/{cycle_id}/review")
def review(cycle_id: str, payload: ImprovementReviewRequest) -> dict[str, object]:
    try:
        return SelfImprovementEngine().review(cycle_id, tests_passed=payload.tests_passed, review_accepted=payload.review_accepted, acceptance_met=payload.acceptance_met, regressions=payload.regressions, review_summary=str(payload.notes), follow_up_tasks=payload.follow_up_tasks, confidence=payload.confidence)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Cycle not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post("/cycles/{cycle_id}/rollback")
def rollback(cycle_id: str, payload: ImprovementRollbackRequest) -> dict[str, object]:
    try:
        return SelfImprovementEngine().rollback(cycle_id, execute=payload.execute)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Cycle not found") from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cycles/{cycle_id}/interrupt")
def interrupt(cycle_id: str, payload: ImprovementInterruptRequest) -> dict[str, object]:
    try:
        return SelfImprovementEngine().interrupt(cycle_id, payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Cycle not found") from exc

@router.post("/cycles/{cycle_id}/resume")
def resume(cycle_id: str) -> dict[str, object]:
    try:
        return SelfImprovementEngine().resume(cycle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Cycle not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/cycles")
def cycles(project_id: str | None = None, candidate_id: str | None = None,
           limit: int = Query(default=50, ge=1, le=100)) -> dict[str, object]:
    return {"cycles": SelfImprovementEngine().list_cycles(project_id, candidate_id=candidate_id, limit=limit)}
