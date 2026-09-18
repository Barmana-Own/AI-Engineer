from __future__ import annotations
from collections import Counter
from fastapi import APIRouter, HTTPException, Query
from app.db import get_project
from app.schemas import CoordinationFailureRequest, CoordinationHandoffRequest, CoordinationMessageRequest, CoordinationResultRequest, CoordinationRevisionRequest, CoordinationRunRequest
from app.coordination.bus import MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.roles import list_role_contracts
from app.coordination import store
from app.coordination.supervisor import Supervisor
router=APIRouter(prefix="/v1/coordination",tags=["coordination"])
def _supervisor() -> Supervisor: return Supervisor()
@router.get("/roles")
def roles() -> dict[str,object]: return {"roles":list_role_contracts()}
@router.post("/runs")
def create_run(payload: CoordinationRunRequest) -> dict[str,object]:
    if not get_project(payload.project_id): raise HTTPException(status_code=404,detail="Project not found")
    try: return _supervisor().start_objective(project_id=payload.project_id,objective=payload.objective)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
@router.get("/runs/{run_id}")
def run_status(run_id: str) -> dict[str,object]: return _supervisor().status(run_id)
@router.get("/tasks")
def tasks(project_id: str|None=None, run_id: str|None=None, state: str|None=None, limit: int=Query(default=100,ge=1,le=500)) -> dict[str,object]:
    states=(state,) if state else ()
    return {"tasks":store.list_tasks(project_id=project_id,run_id=run_id,states=states,limit=limit)}
@router.get("/dependencies")
def dependencies(task_id: str|None=None) -> dict[str,object]: return {"dependencies":store.list_dependencies(task_id)}
@router.get("/messages")
def messages(run_id: str|None=None, project_id: str|None=None, task_id: str|None=None, limit: int=Query(default=100,ge=1,le=500)) -> dict[str,object]: return {"messages":store.list_messages(run_id=run_id,project_id=project_id,task_id=task_id,limit=limit)}
@router.post("/messages")
def publish_message(payload: CoordinationMessageRequest) -> dict[str,object]:
    try: kind=MessageType(payload.message_type.upper())
    except ValueError as exc: raise HTTPException(status_code=400,detail="Unsupported message type") from exc
    return MessageBus().publish(sender_role=payload.sender_role,recipient_role=payload.recipient_role,message_type=kind,subject=payload.subject,body=payload.body,run_id=payload.run_id,project_id=payload.project_id,task_id=payload.task_id,references=payload.references,discussion_round=payload.discussion_round)
@router.get("/handoffs")
def handoffs(run_id: str|None=None, project_id: str|None=None, task_id: str|None=None, limit: int=Query(default=100,ge=1,le=500)) -> dict[str,object]: return {"handoffs":store.list_handoffs(run_id=run_id,project_id=project_id,task_id=task_id,limit=limit)}
@router.post("/handoffs")
def create_handoff(payload: CoordinationHandoffRequest) -> dict[str,object]:
    return store.create_handoff(AgentHandoff(sender_role=payload.sender_role,recipient_role=payload.recipient_role,summary=payload.summary,completed=tuple(payload.completed),artifacts=tuple(payload.artifacts),changed_files=tuple(payload.changed_files),decisions=tuple(payload.decisions),risks=tuple(payload.risks),remaining_work=tuple(payload.remaining_work),verification=tuple(payload.verification),run_id=payload.run_id,project_id=payload.project_id,task_id=payload.task_id))
@router.get("/agents/status")
def agent_status(run_id: str|None=None, project_id: str|None=None) -> dict[str,object]:
    rows=store.list_tasks(run_id=run_id,project_id=project_id,limit=500); by_role:dict[str,dict[str,int]]={}
    for row in rows:
        role=str(row["role"]); by_role.setdefault(role,Counter()); by_role[role][str(row["state"])]+=1
    return {"agents":{role:dict(counts) for role,counts in by_role.items()}}
@router.post("/tasks/{task_id}/result")
def task_result(task_id: str,payload: CoordinationResultRequest) -> dict[str,object]:
    try: return _supervisor().record_result(task_id,summary=payload.summary,evidence=payload.evidence,approved=payload.approved)
    except KeyError as exc: raise HTTPException(status_code=404,detail="Task not found") from exc
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
@router.post("/tasks/{task_id}/revision")
def task_revision(task_id: str,payload: CoordinationRevisionRequest) -> dict[str,object]:
    try: return _supervisor().request_revision(task_id,reason=payload.reason)
    except KeyError as exc: raise HTTPException(status_code=404,detail="Task not found") from exc
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
@router.post("/tasks/{task_id}/failure")
def task_failure(task_id: str,payload: CoordinationFailureRequest) -> dict[str,object]:
    try: return _supervisor().record_failure(task_id,reason=payload.reason)
    except KeyError as exc: raise HTTPException(status_code=404,detail="Task not found") from exc


