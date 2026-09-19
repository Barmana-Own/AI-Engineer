from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.coordination.company_trace import build_company_trace, list_events, render_company_trace


router = APIRouter(prefix="/v1/company", tags=["company"])


@router.get("/events")
def company_events(
    project_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
) -> dict:
    return {"events": list_events(project_id=project_id, run_id=run_id, event_type=event_type, limit=limit)}


@router.get("/projects/{project_id}/trace")
def project_trace(project_id: str, run_id: str | None = Query(default=None)) -> dict:
    try:
        return build_company_trace(project_id, run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get("/projects/{project_id}/trace/markdown")
def project_trace_markdown(project_id: str, run_id: str | None = Query(default=None)) -> dict:
    try:
        return {"markdown": render_company_trace(build_company_trace(project_id, run_id=run_id))}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
