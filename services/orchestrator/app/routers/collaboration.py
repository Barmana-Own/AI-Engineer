from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.db import get_project
from app.coordination.collaboration import CollaborationEngine
from app.schemas import (
    CollaborationMessageRequest,
    ConversationCreateRequest,
    DiscussionResolveRequest,
    MeetingCloseRequest,
    MeetingCreateRequest,
    MeetingDecisionRequest,
    MeetingMessageRequest,
    WorkRequestCreateRequest,
    WorkRequestRespondRequest,
)

router = APIRouter(prefix="/v1/collaboration", tags=["collaboration"])


def _engine() -> CollaborationEngine:
    return CollaborationEngine()


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (ValueError, RuntimeError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/conversations")
def conversation_create(request: ConversationCreateRequest) -> dict[str, object]:
    if request.project_id and not get_project(request.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return _engine().create_conversation(**request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/conversations")
def conversations(
    project_id: str | None = Query(default=None, max_length=128),
    conversation_type: str | None = Query(default=None, max_length=32),
    participant: str | None = Query(default=None, max_length=64),
) -> dict[str, object]:
    return {"conversations": _engine().conversations(
        project_id=project_id,
        conversation_type=conversation_type,
        participant=participant,
    )}


@router.post("/conversations/{conversation_id}/messages")
def conversation_message(conversation_id: str, request: CollaborationMessageRequest) -> dict[str, object]:
    try:
        return _engine().send(conversation_id=conversation_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/conversations/{conversation_id}/discussion")
def discussion_message(conversation_id: str, request: CollaborationMessageRequest) -> dict[str, object]:
    try:
        return _engine().discuss(conversation_id=conversation_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/conversations/{conversation_id}/resolve")
def discussion_resolve(conversation_id: str, request: DiscussionResolveRequest) -> dict[str, object]:
    try:
        return _engine().resolve_discussion(conversation_id=conversation_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/meetings")
def meeting_create(request: MeetingCreateRequest) -> dict[str, object]:
    if not get_project(request.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return _engine().start_meeting(**request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/meetings")
def meetings(
    project_id: str | None = Query(default=None, max_length=128),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
) -> dict[str, object]:
    return {"meetings": _engine().meetings(project_id=project_id, status=status_filter)}


@router.post("/meetings/{meeting_id}/messages")
def meeting_message(meeting_id: str, request: MeetingMessageRequest) -> dict[str, object]:
    try:
        return _engine().add_meeting_message(meeting_id=meeting_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/meetings/{meeting_id}/decisions")
def meeting_decision(meeting_id: str, request: MeetingDecisionRequest) -> dict[str, object]:
    try:
        return _engine().record_meeting_decision(meeting_id=meeting_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/meetings/{meeting_id}/close")
def meeting_close(meeting_id: str, request: MeetingCloseRequest) -> dict[str, object]:
    try:
        return _engine().close_meeting(meeting_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/work-requests")
def work_request_create(request: WorkRequestCreateRequest) -> dict[str, object]:
    if not get_project(request.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return _engine().request_help(**request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/work-requests/{request_id}/respond")
def work_request_respond(request_id: str, request: WorkRequestRespondRequest) -> dict[str, object]:
    try:
        return _engine().respond_help(request_id, **request.model_dump())
    except Exception as exc:
        raise _error(exc) from exc
