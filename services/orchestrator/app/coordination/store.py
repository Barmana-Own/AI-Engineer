from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping
from app.db import connect, initialize_database, utc_now
from .models import AgentHandoff, AgentMessage, CoordinationTask, MessageType, TaskState
from .roles import resolve_role
def _json(value: object, default: object) -> str:
    return json.dumps(value if value is not None else default, ensure_ascii=False, separators=(",", ":"))
def _load(value: str | None, default: object) -> object:
    try: return json.loads(value or "")
    except (TypeError, ValueError): return default
def _tuple(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in value) if isinstance(value, list) else ()
def _task(row: sqlite3.Row) -> dict[str, object]:
    return {"id": row["id"], "project_id": row["project_id"], "run_id": row["run_id"], "parent_task_id": row["parent_task_id"], "title": row["title"], "description": row["description"], "role": row["role"], "assigned_agent": row["assigned_agent"], "state": row["state"], "priority": row["priority"], "dependencies": _load(row["dependencies_json"], []), "blocked_by": _load(row["blocked_by_json"], []), "inputs": _load(row["inputs_json"], {}), "expected_outputs": _load(row["expected_outputs_json"], []), "acceptance_criteria": _load(row["acceptance_criteria_json"], []), "retry_count": row["retry_count"], "max_retries": row["max_retries"], "failure_reason": row["failure_reason"], "scope": _load(row["scope_json"], []), "writer": bool(row["writer"]), "created_at": row["created_at"], "started_at": row["started_at"], "completed_at": row["completed_at"], "updated_at": row["updated_at"]}
def create_task(task: CoordinationTask, *, database_path: str | None = None) -> dict[str, object]:
    initialize_database(database_path)
    now=utc_now()
    with connect(database_path) as db:
        db.execute("INSERT INTO coordination_tasks(id,project_id,run_id,parent_task_id,title,description,role,assigned_agent,state,priority,dependencies_json,blocked_by_json,inputs_json,expected_outputs_json,acceptance_criteria_json,retry_count,max_retries,failure_reason,scope_json,writer,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (task.id,task.project_id,task.run_id,task.parent_task_id,task.title[:500],task.description[:20000],resolve_role(task.role),task.assigned_agent,task.state.value,int(task.priority),_json(list(task.dependencies),[]),_json(list(task.blocked_by),[]),_json(dict(task.inputs),{}),_json(list(task.expected_outputs),[]),_json(list(task.acceptance_criteria),[]),int(task.retry_count),int(task.max_retries),task.failure_reason,_json(list(task.scope),[]),int(task.writer),now,now))
        db.executemany("INSERT INTO coordination_task_dependencies(task_id,depends_on_task_id,created_at) VALUES (?,?,?)", [(task.id,d,now) for d in task.dependencies])
        row=db.execute("SELECT * FROM coordination_tasks WHERE id=?",(task.id,)).fetchone()
    return _task(row)
def get_task(task_id: str, *, database_path: str | None = None) -> dict[str, object] | None:
    initialize_database(database_path)
    with connect(database_path) as db: row=db.execute("SELECT * FROM coordination_tasks WHERE id=?",(task_id,)).fetchone()
    return _task(row) if row else None
def list_tasks(*, project_id: str | None=None, run_id: str | None=None, states: tuple[str,...]=(), limit: int=100, database_path: str | None=None) -> list[dict[str, object]]:
    initialize_database(database_path); safe=min(max(int(limit),1),500)
    clauses=[]; values:list[object]=[]
    if project_id: clauses.append("project_id=?"); values.append(project_id)
    if run_id: clauses.append("run_id=?"); values.append(run_id)
    if states: clauses.append("state IN (" + ",".join("?" for _ in states) + ")"); values.extend(states)
    where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
    with connect(database_path) as db: rows=db.execute("SELECT * FROM coordination_tasks"+where+" ORDER BY priority DESC, created_at ASC LIMIT ?",(*values,safe)).fetchall()
    return [_task(row) for row in rows]
_ALLOWED = {"pending": {"ready","blocked","cancelled"}, "ready": {"assigned","blocked","cancelled"}, "assigned": {"running","waiting","blocked","cancelled"}, "running": {"waiting","review","failed","completed","blocked"}, "waiting": {"ready","running","blocked","cancelled"}, "blocked": {"ready","cancelled"}, "review": {"completed","failed","waiting"}, "failed": {"ready","cancelled"}, "completed": set(), "cancelled": set()}
def transition(task_id: str, state: TaskState | str, *, failure_reason: str | None=None, assigned_agent: str | None=None, database_path: str | None=None) -> dict[str, object]:
    initialize_database(database_path); target=state.value if isinstance(state,TaskState) else str(state)
    with connect(database_path) as db:
        row=db.execute("SELECT * FROM coordination_tasks WHERE id=?",(task_id,)).fetchone()
        if not row: raise KeyError(task_id)
        current=str(row["state"])
        if target not in _ALLOWED.get(current,set()): raise ValueError(f"invalid transition {current}->{target}")
        now=utc_now(); started=now if target=="running" and not row["started_at"] else row["started_at"]; completed=now if target in {"completed","cancelled"} else row["completed_at"]
        retry=int(row["retry_count"])+(1 if target=="failed" else 0)
        db.execute("UPDATE coordination_tasks SET state=?,failure_reason=?,assigned_agent=COALESCE(?,assigned_agent),retry_count=?,started_at=?,completed_at=?,updated_at=? WHERE id=?", (target,failure_reason,assigned_agent,retry,started,completed,now,task_id))
        result=db.execute("SELECT * FROM coordination_tasks WHERE id=?",(task_id,)).fetchone()
    return _task(result)
def _message(row: sqlite3.Row) -> dict[str, object]:
    return {
        "message_id": row["message_id"], "run_id": row["run_id"], "project_id": row["project_id"],
        "task_id": row["task_id"], "sender_role": row["sender_role"], "recipient_role": row["recipient_role"],
        "message_type": row["message_type"], "subject": row["subject"], "body": row["body"],
        "references": _load(row["references_json"], []), "discussion_round": row["discussion_round"],
        "conversation_id": row["conversation_id"] if "conversation_id" in row.keys() else None,
        "audience_type": row["audience_type"] if "audience_type" in row.keys() else "direct",
        "audience_id": row["audience_id"] if "audience_id" in row.keys() else None,
        "participant_roles": _load(row["participant_roles_json"], []) if "participant_roles_json" in row.keys() else [],
        "topic": row["topic"] if "topic" in row.keys() else "", "created_at": row["created_at"],
    }

def create_message(message: AgentMessage, *, database_path: str | None=None) -> dict[str, object]:
    initialize_database(database_path); now=utc_now()
    with connect(database_path) as db:
        db.execute("""INSERT INTO agent_messages(
            message_id,run_id,project_id,task_id,sender_role,recipient_role,message_type,subject,body,
            references_json,discussion_round,conversation_id,audience_type,audience_id,participant_roles_json,topic,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            message.message_id,message.run_id,message.project_id,message.task_id,resolve_role(message.sender_role),
            resolve_role(message.recipient_role) if message.recipient_role else None,message.message_type.value,
            message.subject[:500],message.body[:20000],_json(list(message.references),[]),max(int(message.discussion_round),0),
            message.conversation_id,message.audience_type,message.audience_id,_json(list(message.participant_roles),[]),
            message.topic[:500],now))
        row=db.execute("SELECT * FROM agent_messages WHERE message_id=?",(message.message_id,)).fetchone()
    return _message(row)

def list_messages(*, run_id: str | None=None, project_id: str | None=None, task_id: str | None=None,
                  conversation_id: str | None=None, audience_type: str | None=None, audience_id: str | None=None,
                  topic: str | None=None, participant_role: str | None=None, limit: int=100,
                  database_path: str | None=None) -> list[dict[str, object]]:
    initialize_database(database_path); clauses=[]; values:list[object]=[]
    for key,val in (("run_id",run_id),("project_id",project_id),("task_id",task_id),("conversation_id",conversation_id),
                    ("audience_type",audience_type),("audience_id",audience_id),("topic",topic)):
        if val: clauses.append(key+"=?"); values.append(val)
    if participant_role:
        clauses.append("(sender_role=? OR recipient_role=? OR participant_roles_json LIKE ?)")
        values.extend((resolve_role(participant_role),resolve_role(participant_role),"%"+participant_role+"%"))
    where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
    with connect(database_path) as db:
        rows=db.execute("SELECT * FROM agent_messages"+where+" ORDER BY created_at ASC LIMIT ?",
                        (*values,min(max(int(limit),1),500))).fetchall()
    return [_message(row) for row in rows]

def _handoff(row: sqlite3.Row) -> dict[str, object]:
    return {"handoff_id":row["handoff_id"],"run_id":row["run_id"],"project_id":row["project_id"],"task_id":row["task_id"],"sender_role":row["sender_role"],"recipient_role":row["recipient_role"],"status":row["status"],"summary":row["summary"],"completed":_load(row["completed_json"],[]),"artifacts":_load(row["artifacts_json"],[]),"changed_files":_load(row["changed_files_json"],[]),"decisions":_load(row["decisions_json"],[]),"risks":_load(row["risks_json"],[]),"remaining_work":_load(row["remaining_work_json"],[]),"verification":_load(row["verification_json"],[]),"created_at":row["created_at"],"updated_at":row["updated_at"]}
def create_handoff(handoff: AgentHandoff, *, database_path: str | None=None) -> dict[str, object]:
    initialize_database(database_path); now=utc_now()
    with connect(database_path) as db:
        db.execute("INSERT INTO coordination_handoffs(handoff_id,run_id,project_id,task_id,sender_role,recipient_role,status,summary,completed_json,artifacts_json,changed_files_json,decisions_json,risks_json,remaining_work_json,verification_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(handoff.handoff_id,handoff.run_id,handoff.project_id,handoff.task_id,resolve_role(handoff.sender_role),resolve_role(handoff.recipient_role),handoff.status,handoff.summary[:20000],_json(list(handoff.completed),[]),_json(list(handoff.artifacts),[]),_json(list(handoff.changed_files),[]),_json(list(handoff.decisions),[]),_json(list(handoff.risks),[]),_json(list(handoff.remaining_work),[]),_json(list(handoff.verification),[]),now,now))
        row=db.execute("SELECT * FROM coordination_handoffs WHERE handoff_id=?",(handoff.handoff_id,)).fetchone()
    return _handoff(row)
def list_handoffs(*, run_id: str | None=None, project_id: str | None=None, task_id: str | None=None, limit: int=100, database_path: str | None=None) -> list[dict[str, object]]:
    initialize_database(database_path); clauses=[]; values:list[object]=[]
    for key,val in (("run_id",run_id),("project_id",project_id),("task_id",task_id)):
        if val: clauses.append(key+"=?"); values.append(val)
    where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
    with connect(database_path) as db: rows=db.execute("SELECT * FROM coordination_handoffs"+where+" ORDER BY created_at ASC LIMIT ?",(*values,min(max(int(limit),1),500))).fetchall()
    return [_handoff(row) for row in rows]
def acquire_lock(resource: str, task_id: str, role: str, *, mode: str="write", lease_seconds: int=1800, database_path: str | None=None) -> bool:
    initialize_database(database_path)
    safe_lease=min(max(int(lease_seconds),60),86400)
    now=datetime.now(timezone.utc)
    expires=(now+timedelta(seconds=safe_lease)).isoformat()
    with connect(database_path) as db:
        # Serialize acquisition so two writers cannot both observe a free resource.
        db.execute("BEGIN IMMEDIATE")
        existing=db.execute("SELECT owner_task_id,mode,expires_at FROM coordination_locks WHERE resource=?",(resource,)).fetchone()
        if existing and existing["owner_task_id"] != task_id:
            expired=False
            raw_expiry=existing["expires_at"]
            if raw_expiry:
                try:
                    expiry=datetime.fromisoformat(str(raw_expiry).replace("Z", "+00:00"))
                    if expiry.tzinfo is None:
                        expiry=expiry.replace(tzinfo=timezone.utc)
                    expired=expiry <= now
                except ValueError:
                    expired=False
            if expired:
                db.execute("DELETE FROM coordination_locks WHERE resource=?",(resource,))
                existing=None
        if existing and existing["owner_task_id"] != task_id:
            return False
        db.execute("INSERT OR REPLACE INTO coordination_locks(resource,owner_task_id,owner_role,mode,acquired_at,expires_at) VALUES (?,?,?,?,?,?)",(resource,task_id,resolve_role(role),mode,now.isoformat(),expires))
    return True

def release_lock(resource: str, task_id: str, *, database_path: str | None=None) -> bool:
    initialize_database(database_path)
    with connect(database_path) as db:
        result=db.execute("DELETE FROM coordination_locks WHERE resource=? AND owner_task_id=?",(resource,task_id))
    return result.rowcount > 0

def resources_available(resources: Iterable[str], task_id: str, *, database_path: str | None = None) -> bool:
    """Return whether a writer can safely claim every requested resource.

    Expired leases are treated as available; acquisition remains the atomic
    operation that removes expired rows and records ownership.
    """
    initialize_database(database_path)
    now = datetime.now(timezone.utc)
    normalized = {str(resource).strip() for resource in resources if str(resource).strip()}
    if not normalized:
        return True
    with connect(database_path) as db:
        rows = db.execute(
            "SELECT resource, owner_task_id, expires_at FROM coordination_locks "
            "WHERE resource IN (" + ",".join("?" for _ in normalized) + ")",
            tuple(sorted(normalized)),
        ).fetchall()
    for row in rows:
        if str(row["owner_task_id"]) == str(task_id):
            continue
        try:
            expiry = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return False
        if expiry > now:
            return False
    return True
def add_dependency(task_id: str, depends_on_task_id: str, *, database_path: str | None = None) -> dict[str, object]:
    """Add an idempotent, project-local DAG edge with cycle protection."""
    initialize_database(database_path)
    child_id = str(task_id).strip()
    dependency_id = str(depends_on_task_id).strip()
    if not child_id or not dependency_id:
        raise ValueError("task and dependency ids are required")
    if child_id == dependency_id:
        raise ValueError("a task cannot depend on itself")
    with connect(database_path) as db:
        child = db.execute("SELECT * FROM coordination_tasks WHERE id=?", (child_id,)).fetchone()
        dependency = db.execute("SELECT * FROM coordination_tasks WHERE id=?", (dependency_id,)).fetchone()
        if not child:
            raise KeyError(child_id)
        if not dependency:
            raise KeyError(dependency_id)
        if str(child["project_id"]) != str(dependency["project_id"]):
            raise ValueError("task dependencies must remain within one project")
        graph: dict[str, list[str]] = {}
        for edge in db.execute("SELECT task_id, depends_on_task_id FROM coordination_task_dependencies").fetchall():
            graph.setdefault(str(edge["task_id"]), []).append(str(edge["depends_on_task_id"]))
        stack = [dependency_id]
        visited: set[str] = set()
        while stack:
            current = stack.pop()
            if current == child_id:
                raise ValueError("dependency would create a cycle")
            if current in visited:
                continue
            visited.add(current)
            stack.extend(graph.get(current, ()))
        now = utc_now()
        db.execute(
            "INSERT OR IGNORE INTO coordination_task_dependencies(task_id,depends_on_task_id,created_at) VALUES (?,?,?)",
            (child_id, dependency_id, now),
        )
        current_deps = list(_load(child["dependencies_json"], []))
        if dependency_id not in current_deps:
            current_deps.append(dependency_id)
            db.execute(
                "UPDATE coordination_tasks SET dependencies_json=?,updated_at=? WHERE id=?",
                (_json(current_deps, []), now, child_id),
            )
        result = db.execute("SELECT * FROM coordination_tasks WHERE id=?", (child_id,)).fetchone()
    return _task(result)

def list_dependencies(task_id: str | None=None, *, database_path: str | None=None) -> list[dict[str, str]]:
    initialize_database(database_path)
    with connect(database_path) as db:
        if task_id: rows=db.execute("SELECT task_id,depends_on_task_id FROM coordination_task_dependencies WHERE task_id=?",(task_id,)).fetchall()
        else: rows=db.execute("SELECT task_id,depends_on_task_id FROM coordination_task_dependencies ORDER BY task_id").fetchall()
    return [{"task_id":row["task_id"],"depends_on_task_id":row["depends_on_task_id"]} for row in rows]

