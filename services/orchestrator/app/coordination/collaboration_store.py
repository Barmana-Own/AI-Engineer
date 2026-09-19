
from __future__ import annotations
import json
import sqlite3
from typing import Iterable
from uuid import uuid4

from app.db import connect, initialize_database, utc_now
from .models import ConversationType, InternalWorkRequest, MeetingType, StructuredMeeting, TechnicalDecision, WorkRequestStatus

MAX = 20000

def _json(value: object, default: object = None) -> str:
    return json.dumps(value if value is not None else (default if default is not None else []), ensure_ascii=False, separators=(",", ":"))

def _load(value: str | None, default: object = None) -> object:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return default if default is not None else []

def _items(values: Iterable[object] | None, limit: int = 100) -> list[str]:
    out: list[str] = []
    for value in values or ():
        item = str(value or "").strip()[:2000]
        if item and item not in out:
            out.append(item)
        if len(out) >= limit:
            break
    return out

def _ensure(database_path: str | None) -> None:
    initialize_database(database_path)

def _conv(row: sqlite3.Row) -> dict[str, object]:
    return {k: row[k] for k in ("conversation_id", "project_id", "run_id", "task_id", "conversation_type", "subject", "topic", "department", "status", "created_at", "updated_at")} | {"participants": _load(row["participants_json"])}

def create_conversation(*, project_id: str | None, subject: str, conversation_type: ConversationType | str = ConversationType.DIRECT, participants: Iterable[str] = (), topic: str = "", department: str | None = None, run_id: str | None = None, task_id: str | None = None, conversation_id: str | None = None, database_path: str | None = None) -> dict[str, object]:
    _ensure(database_path)
    kind = conversation_type.value if isinstance(conversation_type, ConversationType) else str(conversation_type)
    if kind not in {x.value for x in ConversationType}:
        raise ValueError("unsupported conversation type")
    if not str(subject or "").strip():
        raise ValueError("conversation subject is required")
    ident, now = conversation_id or str(uuid4()), utc_now()
    with connect(database_path) as db:
        db.execute("INSERT INTO coordination_conversations(conversation_id,project_id,run_id,task_id,conversation_type,subject,topic,participants_json,department,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,'open',?,?)", (ident, project_id, run_id, task_id, kind, str(subject)[:500], str(topic)[:500], _json(_items(participants)), str(department or "")[:64] or None, now, now))
        return _conv(db.execute("SELECT * FROM coordination_conversations WHERE conversation_id=?", (ident,)).fetchone())

def get_conversation(conversation_id: str, *, database_path: str | None = None) -> dict[str, object] | None:
    _ensure(database_path)
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM coordination_conversations WHERE conversation_id=?", (conversation_id,)).fetchone()
    return _conv(row) if row else None

def list_conversations(*, project_id: str | None = None, run_id: str | None = None, conversation_type: str | None = None, participant: str | None = None, limit: int = 100, database_path: str | None = None) -> list[dict[str, object]]:
    _ensure(database_path); clauses=[]; values=[]
    for key, value in (("project_id", project_id), ("run_id", run_id), ("conversation_type", conversation_type)):
        if value: clauses.append(key+"=?"); values.append(value)
    if participant: clauses.append("participants_json LIKE ?"); values.append("%"+participant+"%")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect(database_path) as db:
        rows = db.execute("SELECT * FROM coordination_conversations"+where+" ORDER BY updated_at DESC LIMIT ?", (*values, min(max(int(limit),1),500))).fetchall()
    return [_conv(row) for row in rows]

def _decision(row: sqlite3.Row) -> dict[str, object]:
    return {k: row[k] for k in ("decision_id", "project_id", "run_id", "meeting_id", "title", "context", "decision", "decision_maker", "created_at", "superseded_by")} | {k: _load(row[k+"_json"]) for k in ("options", "arguments", "supporting_evidence", "affected_tasks")}

def create_decision(decision: TechnicalDecision, *, database_path: str | None = None) -> dict[str, object]:
    _ensure(database_path)
    with connect(database_path) as db:
        db.execute("INSERT INTO coordination_decisions(decision_id,project_id,run_id,meeting_id,title,context,options_json,arguments_json,decision,decision_maker,supporting_evidence_json,affected_tasks_json,created_at,superseded_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (decision.decision_id, decision.project_id, decision.run_id, decision.meeting_id, decision.title[:500], decision.context[:MAX], _json(_items(decision.options)), _json(_items(decision.arguments)), decision.decision[:MAX], decision.decision_maker[:128], _json(_items(decision.supporting_evidence)), _json(_items(decision.affected_tasks)), utc_now(), decision.superseded_by))
        return _decision(db.execute("SELECT * FROM coordination_decisions WHERE decision_id=?", (decision.decision_id,)).fetchone())

def get_decision(decision_id: str, *, database_path: str | None = None) -> dict[str, object] | None:
    _ensure(database_path)
    with connect(database_path) as db:
        row=db.execute("SELECT * FROM coordination_decisions WHERE decision_id=?", (decision_id,)).fetchone()
    return _decision(row) if row else None

def supersede_decision(decision_id: str, replacement_id: str, *, database_path: str | None = None) -> dict[str, object] | None:
    _ensure(database_path)
    with connect(database_path) as db:
        db.execute("UPDATE coordination_decisions SET superseded_by=? WHERE decision_id=?", (replacement_id, decision_id))
        row=db.execute("SELECT * FROM coordination_decisions WHERE decision_id=?", (decision_id,)).fetchone()
    return _decision(row) if row else None

def list_decisions(*, project_id: str | None = None, run_id: str | None = None, meeting_id: str | None = None, limit: int = 100, database_path: str | None = None) -> list[dict[str, object]]:
    _ensure(database_path); clauses=[]; values=[]
    for key, value in (("project_id", project_id), ("run_id", run_id), ("meeting_id", meeting_id)):
        if value: clauses.append(key+"=?"); values.append(value)
    where=" WHERE "+" AND ".join(clauses) if clauses else ""
    with connect(database_path) as db:
        rows=db.execute("SELECT * FROM coordination_decisions"+where+" ORDER BY created_at ASC LIMIT ?", (*values, min(max(int(limit),1),500))).fetchall()
    return [_decision(row) for row in rows]

def _meeting(row: sqlite3.Row) -> dict[str, object]:
    base={k: row[k] for k in ("meeting_id","project_id","run_id","meeting_type","objective","status","started_at","ended_at","created_at","updated_at")}
    return base | {k: _load(row[k+"_json"]) for k in ("participants","agenda","message_ids","decision_ids","action_items","unresolved_questions")}

def create_meeting(meeting: StructuredMeeting, *, database_path: str | None = None) -> dict[str, object]:
    _ensure(database_path)
    kind=meeting.meeting_type.value if isinstance(meeting.meeting_type, MeetingType) else str(meeting.meeting_type)
    if kind not in {x.value for x in MeetingType}: raise ValueError("unsupported meeting type")
    if not meeting.participants: raise ValueError("meeting requires participants")
    with connect(database_path) as db:
        db.execute("INSERT INTO coordination_meetings(meeting_id,project_id,run_id,meeting_type,objective,participants_json,agenda_json,message_ids_json,decision_ids_json,action_items_json,unresolved_questions_json,status,started_at,ended_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (meeting.meeting_id, meeting.project_id, meeting.run_id, kind, meeting.objective[:MAX], _json(_items(meeting.participants)), _json(_items(meeting.agenda)), _json(_items(meeting.message_ids)), _json(_items(meeting.decision_ids)), _json(_items(meeting.action_items)), _json(_items(meeting.unresolved_questions)), meeting.status, meeting.started_at, meeting.ended_at, utc_now(), utc_now()))
        return _meeting(db.execute("SELECT * FROM coordination_meetings WHERE meeting_id=?", (meeting.meeting_id,)).fetchone())

def get_meeting(meeting_id: str, *, database_path: str | None = None) -> dict[str, object] | None:
    _ensure(database_path)
    with connect(database_path) as db: row=db.execute("SELECT * FROM coordination_meetings WHERE meeting_id=?", (meeting_id,)).fetchone()
    return _meeting(row) if row else None

def list_meetings(*, project_id: str | None = None, run_id: str | None = None, status: str | None = None, limit: int = 100, database_path: str | None = None) -> list[dict[str, object]]:
    _ensure(database_path); clauses=[]; values=[]
    for key, value in (("project_id", project_id), ("run_id", run_id), ("status", status)):
        if value: clauses.append(key+"=?"); values.append(value)
    where=" WHERE "+" AND ".join(clauses) if clauses else ""
    with connect(database_path) as db:
        rows=db.execute("SELECT * FROM coordination_meetings"+where+" ORDER BY updated_at DESC LIMIT ?", (*values, min(max(int(limit),1),500))).fetchall()
    return [_meeting(row) for row in rows]

def update_meeting(meeting_id: str, *, status: str | None = None, message_ids: Iterable[str] | None = None, decision_ids: Iterable[str] | None = None, action_items: Iterable[str] | None = None, unresolved_questions: Iterable[str] | None = None, database_path: str | None = None) -> dict[str, object]:
    _ensure(database_path)
    with connect(database_path) as db:
        row=db.execute("SELECT * FROM coordination_meetings WHERE meeting_id=?", (meeting_id,)).fetchone()
        if not row: raise KeyError(meeting_id)
        fields=["updated_at=?"]; values=[utc_now()]
        if status is not None:
            fields.append("status=?"); values.append(status)
            if status=="active" and not row["started_at"]: fields.append("started_at=?"); values.append(utc_now())
            if status in {"completed","cancelled"}: fields.append("ended_at=?"); values.append(utc_now())
        for col, val in (("message_ids_json",message_ids),("decision_ids_json",decision_ids),("action_items_json",action_items),("unresolved_questions_json",unresolved_questions)):
            if val is not None: fields.append(col+"=?"); values.append(_json(_items(val)))
        values.append(meeting_id); db.execute("UPDATE coordination_meetings SET "+", ".join(fields)+" WHERE meeting_id=?", values)
        return _meeting(db.execute("SELECT * FROM coordination_meetings WHERE meeting_id=?", (meeting_id,)).fetchone())

def _request(row: sqlite3.Row) -> dict[str, object]:
    return {k: row[k] for k in ("request_id","sender","recipient","project_id","run_id","task_id","request_type","description","priority","status","response","created_at","updated_at","resolved_at")}

def create_work_request(request: InternalWorkRequest, *, database_path: str | None = None) -> dict[str, object]:
    _ensure(database_path); status=request.status.value if isinstance(request.status, WorkRequestStatus) else str(request.status)
    if status not in {x.value for x in WorkRequestStatus}: raise ValueError("unsupported work request status")
    with connect(database_path) as db:
        db.execute("INSERT INTO agent_work_requests(request_id,sender,recipient,project_id,run_id,task_id,request_type,description,priority,status,response,created_at,updated_at,resolved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (request.request_id,request.sender[:128],request.recipient[:128],request.project_id,request.run_id,request.task_id,request.request_type[:128],request.description[:MAX], max(0,min(int(request.priority),100)), status, request.response[:MAX], utc_now(), utc_now(), request.resolved_at))
        return _request(db.execute("SELECT * FROM agent_work_requests WHERE request_id=?", (request.request_id,)).fetchone())

def get_work_request(request_id: str, *, database_path: str | None = None) -> dict[str, object] | None:
    _ensure(database_path)
    with connect(database_path) as db: row=db.execute("SELECT * FROM agent_work_requests WHERE request_id=?", (request_id,)).fetchone()
    return _request(row) if row else None

def list_work_requests(*, project_id: str | None = None, recipient: str | None = None, status: str | None = None, limit: int = 100, database_path: str | None = None) -> list[dict[str, object]]:
    _ensure(database_path); clauses=[]; values=[]
    for key, value in (("project_id", project_id),("recipient",recipient),("status",status)):
        if value: clauses.append(key+"=?"); values.append(value)
    where=" WHERE "+" AND ".join(clauses) if clauses else ""
    with connect(database_path) as db:
        rows=db.execute("SELECT * FROM agent_work_requests"+where+" ORDER BY priority DESC, created_at ASC LIMIT ?", (*values,min(max(int(limit),1),500))).fetchall()
    return [_request(row) for row in rows]

def update_work_request(request_id: str, *, status: WorkRequestStatus | str | None = None, response: str | None = None, database_path: str | None = None) -> dict[str, object]:
    _ensure(database_path)
    with connect(database_path) as db:
        row=db.execute("SELECT * FROM agent_work_requests WHERE request_id=?", (request_id,)).fetchone()
        if not row: raise KeyError(request_id)
        fields=["updated_at=?"]; values=[utc_now()]
        if status is not None:
            clean=status.value if isinstance(status, WorkRequestStatus) else str(status)
            if clean not in {x.value for x in WorkRequestStatus}: raise ValueError("unsupported work request status")
            fields.append("status=?"); values.append(clean)
            if clean in {WorkRequestStatus.ANSWERED.value,WorkRequestStatus.DECLINED.value,WorkRequestStatus.CANCELLED.value}: fields.append("resolved_at=?"); values.append(utc_now())
        if response is not None: fields.append("response=?"); values.append(str(response)[:MAX])
        values.append(request_id); db.execute("UPDATE agent_work_requests SET "+", ".join(fields)+" WHERE request_id=?", values)
        return _request(db.execute("SELECT * FROM agent_work_requests WHERE request_id=?", (request_id,)).fetchone())
