
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.coordination import incidents
from app.coordination import owner_control
from app.db import get_project
from app.schemas import (
    CollaborationQualityRequest,
    IncidentCreateRequest,
    IncidentTeamRequest,
    IncidentTransitionRequest,
    OpportunityCreateRequest,
    OpportunityAnalyzeRequest,
    OpportunityConvertRequest,
    OpportunityQualifyRequest,
    OpportunityStartRequest,
    OrganizationalLessonRequest,
    OwnerActionRequest,
    OwnerResolutionRequest,
    PostmortemCreateRequest,
)

router = APIRouter(prefix="/v1", tags=["incidents-owner-control"])


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/incidents")
def incident_create(request: IncidentCreateRequest) -> dict[str, object]:
    try:
        return incidents.create_incident(
            request.project_id,
            request.title,
            request.trigger,
            severity=request.severity,
            description=request.description,
            impact=request.impact,
            run_id=request.run_id,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/incidents")
def incident_list(
    project_id: str | None = Query(default=None, max_length=128),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
) -> dict[str, object]:
    return {"items": incidents.list_incidents(project_id=project_id, status=status_filter)}


@router.get("/incidents/{incident_id}")
def incident_get(incident_id: str) -> dict[str, object]:
    item = incidents.get_incident(incident_id)
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return item


@router.post("/incidents/{incident_id}/transition")
def incident_transition(
    incident_id: str, request: IncidentTransitionRequest
) -> dict[str, object]:
    try:
        return incidents.transition_incident(
            incident_id,
            request.phase,
            actor_role=request.actor_role,
            details=request.details,
            evidence=request.evidence,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/incidents/{incident_id}/events")
def incident_events(incident_id: str) -> dict[str, object]:
    if not incidents.get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found.")
    return {"items": incidents.list_incident_events(incident_id)}


@router.post("/incidents/{incident_id}/team")
def incident_team(
    incident_id: str, request: IncidentTeamRequest
) -> dict[str, object]:
    try:
        return {
            "incident_id": incident_id,
            "members": incidents.assign_incident_team(
                incident_id,
                roles=request.roles or incidents._TEAM_ROLES,
                domain=request.domain,
            ),
        }
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/incidents/{incident_id}/team")
def incident_team_list(incident_id: str) -> dict[str, object]:
    if not incidents.get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found.")
    return {"incident_id": incident_id, "members": incidents.list_incident_team(incident_id)}


@router.post("/incidents/{incident_id}/postmortem")
def postmortem_create(
    incident_id: str, request: PostmortemCreateRequest
) -> dict[str, object]:
    try:
        return incidents.create_postmortem(
            incident_id,
            what_happened=request.what_happened,
            impact=request.impact,
            timeline=request.timeline,
            root_cause=request.root_cause,
            contributing_factors=request.contributing_factors,
            repair=request.repair,
            verification=request.verification,
            prevention_ideas=request.prevention_ideas,
            follow_up_tasks=request.follow_up_tasks,
            created_by=request.created_by,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/postmortems/{postmortem_id}/lesson")
def postmortem_lesson(
    postmortem_id: str, request: OrganizationalLessonRequest
) -> dict[str, object]:
    try:
        return incidents.promote_postmortem_lesson(
            postmortem_id,
            summary=request.summary,
            evidence=request.evidence,
            target=request.target,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/postmortems")
def postmortem_list(
    project_id: str | None = Query(default=None, max_length=128),
) -> dict[str, object]:
    return {"items": incidents.list_postmortems(project_id=project_id)}


@router.get("/organizational/lessons")
def organizational_lessons(
    query: str = Query(default="", max_length=500),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, object]:
    return {"items": incidents.list_organizational_lessons(query=query, limit=limit)}


@router.post("/organizational/collaboration-quality")
def collaboration_quality(request: CollaborationQualityRequest) -> dict[str, object]:
    try:
        return incidents.record_collaboration_issue(
            request.issue_type,
            request.signature,
            severity=request.severity,
            example=request.example,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/organizational/collaboration-quality")
def collaboration_quality_list(
    project_id: str | None = Query(default=None, max_length=128),
) -> dict[str, object]:
    return {"items": incidents.list_collaboration_quality(project_id=project_id)}


@router.get("/organizational/performance")
def organizational_performance(
    role: str | None = Query(default=None, max_length=128),
    model_profile: str | None = Query(default=None, max_length=128),
    domain: str | None = Query(default=None, max_length=128),
) -> dict[str, object]:
    from app.memory import MemoryStore
    return {"items": MemoryStore().performance(role=role, model_profile=model_profile, domain=domain)}


@router.get("/organizational/team-selection")
def team_selection(
    role: str = Query(..., min_length=1, max_length=128),
    domain: str = Query(default="", max_length=128),
) -> dict[str, object]:
    try:
        return incidents.select_agent_for_role(role, domain=domain)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/owner/actions")
def owner_action(request: OwnerActionRequest) -> dict[str, object]:
    try:
        return owner_control.request_owner_action(
            request.action,
            project_id=request.project_id,
            reason=request.reason,
            payload=request.payload,
            requested_by=request.requested_by,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/owner/actions")
def owner_action_list(
    project_id: str | None = Query(default=None, max_length=128),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
) -> dict[str, object]:
    return {"items": owner_control.list_owner_actions(project_id=project_id, status=status_filter)}


@router.post("/owner/actions/{action_id}/resolve")
def owner_action_resolve(
    action_id: str, request: OwnerResolutionRequest
) -> dict[str, object]:
    try:
        return owner_control.resolve_owner_action(
            action_id,
            approved=request.approved,
            actor=request.actor,
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/opportunities")
def opportunity_create(request: OpportunityCreateRequest) -> dict[str, object]:
    try:
        from app.organization.intake import OpportunityIntakeService
        return OpportunityIntakeService().receive(source=request.source, title=request.title, body=request.summary, requirements=request.requirements, external_ref=request.external_ref)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/opportunities/{opportunity_id}")
def opportunity_get(opportunity_id: str) -> dict[str, object]:
    item = owner_control.get_project_opportunity(opportunity_id)
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return item


@router.post("/opportunities/{opportunity_id}/analyze")
def opportunity_analyze(opportunity_id: str, request: OpportunityAnalyzeRequest) -> dict[str, object]:
    try:
        from app.organization.intake import OpportunityIntakeService
        return OpportunityIntakeService().analyze(opportunity_id, company_capabilities=request.company_capabilities)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/opportunities/{opportunity_id}/qualify")
def opportunity_qualify(opportunity_id: str, request: OpportunityQualifyRequest) -> dict[str, object]:
    try:
        from app.organization.intake import OpportunityIntakeService
        return OpportunityIntakeService().qualify(opportunity_id, owner_approved=request.owner_approved)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/opportunities/{opportunity_id}/convert")
def opportunity_convert(opportunity_id: str, request: OpportunityConvertRequest) -> dict[str, object]:
    try:
        from app.organization.intake import OpportunityIntakeService
        return OpportunityIntakeService().convert(opportunity_id, project_name=request.project_name, workspace=request.workspace, objective=request.objective, owner_approved=request.owner_approved)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/opportunities/{opportunity_id}/start")
def opportunity_start(opportunity_id: str, request: OpportunityStartRequest) -> dict[str, object]:
    try:
        from app.organization.intake import OpportunityIntakeService
        return OpportunityIntakeService().start(opportunity_id, objective=request.objective)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/opportunities")
def opportunity_list(
    status_filter: str | None = Query(default=None, alias="status", max_length=64),
) -> dict[str, object]:
    return {"items": owner_control.list_project_opportunities(status=status_filter)}

