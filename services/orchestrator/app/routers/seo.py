"""SEO analysis routes layered on the existing project/task infrastructure."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.agent_service import run_agent_task
from app.config import settings
from app.db import create_task, get_project, get_task
from app.seo_engine.engine import SEOEngine
from app.seo_engine.models import CrawlPolicy, Platform, SourceMode, SeoSiteProfile
from app.seo_engine.persistence import (
    create_site,
    get_finding,
    get_site,
    get_snapshot,
    list_findings,
    list_pages,
    list_sites,
    list_snapshots,
    compare_snapshots,
    save_keyword_plan,
    save_snapshot,
    update_finding_status,
)
from app.seo_engine.security import SafeHttpClient, UnsafeTargetError, validate_url
from app.seo_schemas import (
    SeoAuditRequest,
    SeoDelegateRequest,
    SeoKeywordRequest,
    SeoSiteCreateRequest,
    SeoSiteResponse,
    SeoVerifyRequest,
)
from app.skill_routing import SkillRouteRequest, SkillRouter, SkillRoutingError


router = APIRouter(prefix="/v1/seo", tags=["seo"])
engine = SEOEngine()


def _validate_workspace(value: str | None) -> str | None:
    if not value:
        return None
    candidate = Path(value).expanduser()
    root = Path(settings.workspace_root).expanduser().resolve()
    self_root = Path(settings.self_workspace_root).expanduser().resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not (resolved == root or root in resolved.parents or resolved == self_root or self_root in resolved.parents):
        raise ValueError("SEO workspace escapes the configured project roots.")
    return str(resolved)

def _profile(row: dict[str, Any]) -> SeoSiteProfile:
    return SeoSiteProfile(
        site_id=row["id"], project_id=row["project_id"], name=row["name"], base_url=row.get("base_url"),
        source_mode=SourceMode(row["source_mode"]), workspace=row.get("workspace"), platform=Platform(row.get("platform", "unknown")),
        language=row.get("language"), region=row.get("region"), crawl_policy=CrawlPolicy(**(row.get("crawl_policy") or {})),
    )


def _site_response(row: dict[str, Any]) -> SeoSiteResponse:
    return SeoSiteResponse(
        id=row["id"], project_id=row["project_id"], name=row["name"], base_url=row.get("base_url"),
        platform=row.get("platform", "unknown"), source_mode=row["source_mode"], workspace=row.get("workspace"),
        language=row.get("language"), region=row.get("region"), status=row.get("status", "active"),
        crawl_policy=row.get("crawl_policy") or {}, rendering_mode=row.get("rendering_mode", "raw"),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


@router.post("/sites", response_model=SeoSiteResponse, status_code=status.HTTP_201_CREATED)
def site_create(request: SeoSiteCreateRequest) -> SeoSiteResponse:
    if not get_project(request.project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    if request.source_mode in {"public_url_only", "public_url_and_source", "wordpress_api"}:
        if not request.base_url:
            raise HTTPException(status_code=422, detail="base_url is required for the selected source mode.")
        try:
            validate_url(request.base_url, allow_local=request.allow_local)
        except UnsafeTargetError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        safe_workspace = _validate_workspace(request.workspace)
        site = engine.register_site(
            project_id=request.project_id, name=request.name, base_url=request.base_url,
            source_mode=SourceMode(request.source_mode), workspace=safe_workspace,
            language=request.language, region=request.region,
            crawl_policy=CrawlPolicy(max_pages=request.max_pages, max_depth=request.max_depth),
        )
        return _site_response(create_site(site))
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sites", response_model=list[SeoSiteResponse])
def sites_list(project_id: str | None = None, limit: int = Query(100, ge=1, le=200)) -> list[SeoSiteResponse]:
    if project_id and not get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return [_site_response(row) for row in list_sites(project_id, limit=limit)]


@router.get("/sites/{site_id}", response_model=SeoSiteResponse)
def site_get(site_id: str) -> SeoSiteResponse:
    row = get_site(site_id)
    if not row:
        raise HTTPException(status_code=404, detail="SEO site not found.")
    return _site_response(row)


@router.post("/sites/{site_id}/detect-platform", response_model=SeoSiteResponse)
def site_detect_platform(site_id: str, request: SeoAuditRequest) -> SeoSiteResponse:
    row = get_site(site_id)
    if not row:
        raise HTTPException(status_code=404, detail="SEO site not found.")
    try:
        profile = engine.get_site(site_id)
        if profile is None:
            profile = _profile(row)
            engine._sites[site_id] = profile
        if request.html is not None:
            profile = engine.detect_platform(site_id, html=request.html)
        elif profile.workspace:
            profile = engine.detect_platform(site_id)
        else:
            profile = profile
        with __import__("app.db", fromlist=["connect"]).connect() as database:
            database.execute("UPDATE seo_sites SET platform = ?, updated_at = ? WHERE id = ?", (profile.platform.value, __import__("app.db", fromlist=["utc_now"]).utc_now(), site_id))
        updated = get_site(site_id)
        return _site_response(updated or row)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sites/{site_id}/audits")
def site_audit(site_id: str, request: SeoAuditRequest) -> dict[str, Any]:
    row = get_site(site_id)
    if not row:
        raise HTTPException(status_code=404, detail="SEO site not found.")
    profile = engine.get_site(site_id)
    if profile is None:
        profile = _profile(row)
        engine._sites[site_id] = profile
    fetch = None
    if profile.base_url and profile.source_mode != SourceMode.SOURCE_CODE_ONLY:
        fetch = SafeHttpClient(allow_local=False, timeout_seconds=profile.crawl_policy.timeout_seconds, max_response_bytes=profile.crawl_policy.max_response_bytes).fetch
    try:
        result = engine.audit(site_id, fetch=fetch, baseline=request.baseline, html=request.html)
    except (ValueError, KeyError, UnsafeTargetError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    saved = save_snapshot(result.snapshot)
    return {"snapshot": saved, "findings": list_findings(site_id, snapshot_id=result.snapshot.snapshot_id)}


@router.get("/sites/{site_id}/audits/compare")
def audits_compare(site_id: str, baseline_id: str = Query(..., min_length=1, max_length=120), current_id: str = Query(..., min_length=1, max_length=120)) -> dict[str, Any]:
    site = get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="SEO site not found.")
    comparison = compare_snapshots(baseline_id, current_id)
    if not comparison or comparison["site_id"] != site_id:
        raise HTTPException(status_code=404, detail="SEO audit snapshots not found for this site.")
    return comparison

@router.get("/sites/{site_id}/audits")
def site_audits(site_id: str, limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    if not get_site(site_id):
        raise HTTPException(status_code=404, detail="SEO site not found.")
    return list_snapshots(site_id, limit=limit)


@router.get("/audits/{audit_id}/pages")
def audit_pages(audit_id: str, limit: int = Query(500, ge=1, le=1_000)) -> list[dict[str, Any]]:
    snapshot = get_snapshot(audit_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="SEO audit not found.")
    return list_pages(audit_id, limit=limit)

@router.get("/audits/{audit_id}/findings")
def audit_findings(audit_id: str, limit: int = Query(200, ge=1, le=500)) -> list[dict[str, Any]]:
    snapshot = get_snapshot(audit_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="SEO audit not found.")
    return list_findings(snapshot["site_id"], snapshot_id=audit_id, limit=limit)


@router.post("/sites/{site_id}/keywords")
def site_keywords(site_id: str, request: SeoKeywordRequest) -> dict[str, Any]:
    row = get_site(site_id)
    if not row:
        raise HTTPException(status_code=404, detail="SEO site not found.")
    profile = engine.get_site(site_id)
    if profile is None:
        profile = _profile(row)
        engine._sites[site_id] = profile
    clusters, mappings, briefs = engine.keyword_plan(site_id, request.keywords, pages=request.pages, audience=request.audience, conversion_objective=request.conversion_objective)
    save_keyword_plan(site_id, row["project_id"], clusters, mappings)
    return {"clusters": [item.as_dict() for item in clusters], "maps": [item.as_dict() for item in mappings], "briefs": list(briefs), "data_source": "qualitative; external volume/ranking data not available"}


@router.get("/sites/{site_id}/findings")
def site_findings(site_id: str, limit: int = Query(200, ge=1, le=500)) -> list[dict[str, Any]]:
    if not get_site(site_id):
        raise HTTPException(status_code=404, detail="SEO site not found.")
    return list_findings(site_id, limit=limit)


@router.post("/sites/{site_id}/findings/{finding_id}/delegate")
def finding_delegate(site_id: str, finding_id: str, request: SeoDelegateRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    site = get_site(site_id)
    finding = get_finding(finding_id)
    if not site or not finding or finding["site_id"] != site_id:
        raise HTTPException(status_code=404, detail="SEO finding not found.")
    role = request.assigned_role or finding.get("responsible_role") or "seo_specialist"
    try:
        route = SkillRouter().route(SkillRouteRequest(task_objective=f"SEO finding: {finding['title']}. {finding['recommended_action']}", assigned_role=role, project_type="seo", requirements=[finding["acceptance_criteria"]], risk=finding["severity"], technologies=[], project_phase="seo_analysis", project_id=site["project_id"]))
    except SkillRoutingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    task = create_task(site["project_id"], f"SEO implementation task for {finding['title']}: {finding['recommended_action']}", mode=request.mode, skill_selections=[item.as_dict() for item in route.selections], skill_trace=[{"event": "seo_finding_delegated", "finding_id": finding_id, "site_id": site_id, "role": role, "skill_ids": list(route.skill_ids)}])
    update_finding_status(finding_id, "fix_in_progress", assigned_task_id=task["id"])
    background_tasks.add_task(run_agent_task, task["id"])
    return {"finding": get_finding(finding_id), "task": task}


@router.post("/sites/{site_id}/findings/{finding_id}/verify")
def finding_verify(site_id: str, finding_id: str, request: SeoVerifyRequest) -> dict[str, Any]:
    finding = get_finding(finding_id)
    if not finding or finding["site_id"] != site_id:
        raise HTTPException(status_code=404, detail="SEO finding not found.")
    status_value = "verified" if request.passed else "failed"
    return update_finding_status(finding_id, status_value, evidence=request.evidence) or {}
