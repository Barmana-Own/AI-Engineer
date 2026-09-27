from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable
from uuid import uuid4

from app import db
from app.coordination import store
from app.coordination.collaboration_store import list_decisions, list_work_requests
from app.coordination.models import TaskState

class ProjectPhase(str, Enum):
    INTAKE="intake"; REQUIREMENTS="requirements"; ARCHITECTURE="architecture"
    IMPLEMENTATION="implementation"; INTEGRATION="integration"; TESTING="testing"
    REVIEW="review"; SECURITY_REVIEW="security_review"; RELEASE_VERIFICATION="release_verification"
    COMPLETED="completed"; PAUSED="paused"; FAILED="failed"; CANCELLED="cancelled"

_PHASE_ALIASES={"initiating":ProjectPhase.INTAKE.value}
_TERMINAL={ProjectPhase.COMPLETED.value,ProjectPhase.CANCELLED.value}
_ALLOWED={
 "intake":{"requirements","paused","cancelled"},
 "requirements":{"architecture","implementation","paused","failed","cancelled"},
 "architecture":{"implementation","paused","failed","cancelled"},
 "implementation":{"integration","testing","paused","failed","cancelled"},
 "integration":{"testing","implementation","paused","failed","cancelled"},
 "testing":{"review","implementation","paused","failed","cancelled"},
 "review":{"security_review","release_verification","implementation","failed","paused"},
 "security_review":{"release_verification","implementation","failed","paused"},
 "release_verification":{"completed","implementation","failed","paused"},
 "paused":{"requirements","architecture","implementation","integration","testing","review","security_review","release_verification","cancelled"},
 "failed":{"intake","requirements","implementation","cancelled"},
 "completed":set(),"cancelled":set(),
}
def _now()->str: return datetime.now(timezone.utc).isoformat()
def _json(value:object)->str: return json.dumps(value if value is not None else [],ensure_ascii=False,separators=(",",":"))
def _load(value:str|None)->object:
    try:return json.loads(value or "[]")
    except (TypeError,ValueError):return []
def _norm_phase(value:ProjectPhase|str)->str:
    raw=value.value if isinstance(value,ProjectPhase) else str(value).strip().lower()
    return _PHASE_ALIASES.get(raw,raw)
def _ensure(path:str|None)->None: db.initialize_database(path)

def get_project_state(project_id:str, *, database_path:str|None=None)->dict[str,object]|None:
    _ensure(database_path)
    with db.connect(database_path) as con:
        row=con.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
    if not row:return None
    keys=set(row.keys())
    return {
      "id":row["id"],"name":row["name"],"workspace":row["workspace"],
      "phase":_norm_phase(row["phase"] if "phase" in keys else "intake"),
      "priority":int(row["priority"] if "priority" in keys and row["priority"] is not None else 50),
      "project_manager_id":row["project_manager_id"] if "project_manager_id" in keys else None,
      "engineering_manager_id":row["engineering_manager_id"] if "engineering_manager_id" in keys else None,
      "team_state":row["team_state"] if "team_state" in keys else "forming",
      "updated_at":row["updated_at"],
    }

def _gate_rows(project_id:str, path:str|None)->list[dict[str,object]]:
    _ensure(path)
    with db.connect(path) as con:
        rows=con.execute("SELECT * FROM project_quality_gates WHERE project_id=? ORDER BY gate_name",(project_id,)).fetchall()
    return [{"gate_id":r["gate_id"],"project_id":r["project_id"],"gate_name":r["gate_name"],
             "required":bool(r["required"]),"status":r["status"],"evidence":_load(r["evidence_json"]),
             "updated_at":r["updated_at"]} for r in rows]


def list_quality_gates(project_id: str, *, database_path: str | None = None) -> list[dict[str, object]]:
    return _gate_rows(project_id, database_path)


def set_quality_gate(project_id:str, gate_name:str, *, status:str="pending", required:bool=True,
                     evidence:Iterable[object]=(), database_path:str|None=None)->dict[str,object]:
    allowed={"pending","passed","failed","waived"}
    if status not in allowed: raise ValueError("unsupported quality gate status")
    if not gate_name.strip(): raise ValueError("gate name is required")
    _ensure(database_path); now=_now(); ident=str(uuid4())
    with db.connect(database_path) as con:
        con.execute("""INSERT INTO project_quality_gates(gate_id,project_id,gate_name,required,status,evidence_json,updated_at)
                       VALUES(?,?,?,?,?,?,?)
                       ON CONFLICT(project_id,gate_name) DO UPDATE SET required=excluded.required,status=excluded.status,
                       evidence_json=excluded.evidence_json,updated_at=excluded.updated_at""",
                    (ident,project_id,gate_name.strip()[:200],int(required),status,_json(list(evidence)[:50]),now))
        row=con.execute("SELECT * FROM project_quality_gates WHERE project_id=? AND gate_name=?",(project_id,gate_name.strip()[:200])).fetchone()
    result = {"gate_id":row["gate_id"],"project_id":row["project_id"],"gate_name":row["gate_name"],
            "required":bool(row["required"]),"status":row["status"],"evidence":_load(row["evidence_json"]),
            "updated_at":row["updated_at"]}
    # A rejected review is an explicit delivery signal: reopen implementation
    # while preserving the failed gate and recording the lifecycle transition.
    current_phase = get_project_state(project_id, database_path=database_path)
    if (status == "failed" and gate_name.strip()[:200] == "review_accepted"
            and current_phase and current_phase.get("phase") in {
                ProjectPhase.REVIEW.value,
                ProjectPhase.SECURITY_REVIEW.value,
                ProjectPhase.RELEASE_VERIFICATION.value,
            }):
        transition_project_phase(
            project_id,
            ProjectPhase.IMPLEMENTATION,
            actor_role="project_manager",
            evidence=["review_accepted gate failed"],
            reason="review rejection reopened implementation",
            database_path=database_path,
        )

    return result

def _gate_passed(project_id:str,name:str,path:str|None)->bool:
    rows=_gate_rows(project_id,path)
    found=[r for r in rows if r["gate_name"]==name]
    return bool(found) and any(r["status"] in {"passed","waived"} for r in found)

def transition_project_phase(project_id:str, target:ProjectPhase|str, *, actor_role:str="project_manager",
                             evidence:Iterable[object]=(), reason:str="", database_path:str|None=None)->dict[str,object]:
    _ensure(database_path); new=_norm_phase(target)
    if new not in {p.value for p in ProjectPhase}: raise ValueError("unsupported project phase")
    current=get_project_state(project_id,database_path=database_path)
    if not current: raise KeyError(project_id)
    old=_norm_phase(str(current["phase"]))
    if new==old:return current
    if new not in _ALLOWED.get(old,set()): raise ValueError(f"invalid project transition {old}->{new}")
    evidence_list=[str(x)[:2000] for x in evidence if str(x).strip()]
    if new=="implementation" and not _gate_passed(project_id,"requirements_ready",database_path):
        raise ValueError("requirements_ready quality gate is not passed")
    if new=="release_verification":
        for mandatory in ("tests_passed", "review_accepted"):
            if not _gate_passed(project_id, mandatory, database_path):
                raise ValueError(f"quality gate not passed: {mandatory}")
        for gate in _gate_rows(project_id,database_path):
            if gate["required"] and gate["gate_name"] in {"tests_passed","review_accepted","security_review"} and gate["status"] not in {"passed","waived"}:
                raise ValueError(f"quality gate not passed: {gate['gate_name']}")
    if new=="completed":
        if old!="release_verification": raise ValueError("completion requires release_verification phase")
        if not evidence_list: raise ValueError("completion requires evidence")
        for gate in _gate_rows(project_id,database_path):
            if gate["required"] and gate["status"] not in {"passed","waived"}:
                raise ValueError(f"quality gate not passed: {gate['gate_name']}")
    now=_now(); event_id=str(uuid4())
    with db.connect(database_path) as con:
        con.execute("UPDATE projects SET phase=?,updated_at=? WHERE id=?",(new,now,project_id))
        con.execute("""INSERT INTO project_lifecycle_events(event_id,project_id,from_phase,to_phase,actor_role,evidence_json,reason,created_at)
                       VALUES(?,?,?,?,?,?,?,?)""",(event_id,project_id,old,new,actor_role,_json(evidence_list),reason[:4000],now))
    return get_project_state(project_id,database_path=database_path) or {}

def list_lifecycle_events(project_id:str, *, database_path:str|None=None)->list[dict[str,object]]:
    _ensure(database_path)
    with db.connect(database_path) as con:
        rows=con.execute("SELECT * FROM project_lifecycle_events WHERE project_id=? ORDER BY created_at ASC",(project_id,)).fetchall()
    return [{"event_id":r["event_id"],"project_id":r["project_id"],"from_phase":r["from_phase"],
             "to_phase":r["to_phase"],"actor_role":r["actor_role"],"evidence":_load(r["evidence_json"]),
             "reason":r["reason"],"created_at":r["created_at"]} for r in rows]

def create_milestone(project_id:str,title:str,*,description:str="",state:str="planned",due_at:str|None=None,
                     deliverables:Iterable[object]=(),dependencies:Iterable[object]=(),milestone_id:str|None=None,
                     database_path:str|None=None)->dict[str,object]:
    if state not in {"planned","active","completed","blocked","cancelled"}:raise ValueError("unsupported milestone state")
    if not title.strip():raise ValueError("milestone title is required")
    _ensure(database_path); ident=milestone_id or str(uuid4()); now=_now()
    with db.connect(database_path) as con:
        con.execute("""INSERT INTO project_milestones(milestone_id,project_id,title,description,state,due_at,deliverables_json,dependencies_json,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",(ident,project_id,title[:500],description[:10000],state,due_at,_json(list(deliverables)[:100]),_json(list(dependencies)[:100]),now,now))
        row=con.execute("SELECT * FROM project_milestones WHERE milestone_id=?",(ident,)).fetchone()
    return _milestone(row)
def _milestone(r:sqlite3.Row)->dict[str,object]:
    return {"milestone_id":r["milestone_id"],"project_id":r["project_id"],"title":r["title"],"description":r["description"],
            "state":r["state"],"due_at":r["due_at"],"deliverables":_load(r["deliverables_json"]),
            "dependencies":_load(r["dependencies_json"]),"created_at":r["created_at"],"updated_at":r["updated_at"]}
def list_milestones(project_id:str,*,database_path:str|None=None)->list[dict[str,object]]:
    _ensure(database_path)
    with db.connect(database_path) as con: rows=con.execute("SELECT * FROM project_milestones WHERE project_id=? ORDER BY due_at,created_at",(project_id,)).fetchall()
    return [_milestone(r) for r in rows]

def create_risk(project_id:str,title:str,*,severity:str="medium",status:str="open",mitigation:str="",owner:str|None=None,
                risk_id:str|None=None,database_path:str|None=None)->dict[str,object]:
    if severity not in {"low","medium","high","critical"}:raise ValueError("unsupported risk severity")
    if status not in {"open","mitigated","accepted","closed"}:raise ValueError("unsupported risk status")
    if not title.strip():raise ValueError("risk title is required")
    _ensure(database_path); ident=risk_id or str(uuid4()); now=_now()
    with db.connect(database_path) as con:
        con.execute("""INSERT INTO project_risks(risk_id,project_id,title,severity,status,mitigation,owner,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",(ident,project_id,title[:500],severity,status,mitigation[:10000],owner,now,now))
        row=con.execute("SELECT * FROM project_risks WHERE risk_id=?",(ident,)).fetchone()
    return _risk(row)
def _risk(r:sqlite3.Row)->dict[str,object]:
    return {k:r[k] for k in ("risk_id","project_id","title","severity","status","mitigation","owner","created_at","updated_at")}
def list_risks(project_id:str,*,status:str|None=None,database_path:str|None=None)->list[dict[str,object]]:
    _ensure(database_path); where="project_id=?"; values=[project_id]
    if status:where+=" AND status=?";values.append(status)
    with db.connect(database_path) as con:rows=con.execute("SELECT * FROM project_risks WHERE "+where+" ORDER BY CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,created_at ASC",values).fetchall()
    return [_risk(r) for r in rows]

def enqueue_work(agent_id:str,project_id:str,item_type:str,item_ref:str,*,task_id:str|None=None,priority:int=50,
                 blocked_by:Iterable[object]=(),available_at:str|None=None,queue_id:str|None=None,database_path:str|None=None)->dict[str,object]:
    if not agent_id.strip() or not project_id.strip() or not item_ref.strip():raise ValueError("queue item requires agent, project and reference")
    _ensure(database_path);ident=queue_id or str(uuid4());now=_now()
    with db.connect(database_path) as con:
        con.execute("""INSERT INTO agent_work_queue(queue_id,agent_id,project_id,task_id,item_type,item_ref,priority,status,blocked_by_json,available_at,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(agent_id,item_type,item_ref) DO UPDATE SET priority=excluded.priority,blocked_by_json=excluded.blocked_by_json,updated_at=excluded.updated_at""",
                    (ident,agent_id[:128],project_id,task_id,item_type[:64],item_ref[:256],max(0,min(int(priority),100)),"queued",_json(list(blocked_by)[:100]),available_at,now,now))
        row=con.execute("SELECT * FROM agent_work_queue WHERE agent_id=? AND item_type=? AND item_ref=?",(agent_id,item_type,item_ref)).fetchone()
    return _queue(row)
def _queue(r:sqlite3.Row)->dict[str,object]:
    return {"queue_id":r["queue_id"],"agent_id":r["agent_id"],"project_id":r["project_id"],"task_id":r["task_id"],
            "item_type":r["item_type"],"item_ref":r["item_ref"],"priority":r["priority"],"status":r["status"],
            "blocked_by":_load(r["blocked_by_json"]),"available_at":r["available_at"],"claimed_at":r["claimed_at"],
            "completed_at":r["completed_at"],"created_at":r["created_at"],"updated_at":r["updated_at"]}
def list_work_queue(*,agent_id:str|None=None,project_id:str|None=None,status:str|None=None,limit:int=100,database_path:str|None=None)->list[dict[str,object]]:
    _ensure(database_path); clauses=[];values=[]
    for k,v in (("agent_id",agent_id),("project_id",project_id),("status",status)):
        if v:clauses.append(k+"=?");values.append(v)
    where=" WHERE "+" AND ".join(clauses) if clauses else ""
    with db.connect(database_path) as con:rows=con.execute("SELECT * FROM agent_work_queue"+where+" ORDER BY priority DESC,created_at ASC LIMIT ?",(*values,min(max(int(limit),1),500))).fetchall()
    return [_queue(r) for r in rows]
def claim_next_work(agent_id:str,*,project_id:str|None=None,database_path:str|None=None)->dict[str,object]|None:
    _ensure(database_path);now=_now()
    with db.connect(database_path) as con:
        con.execute("BEGIN IMMEDIATE")
        clauses=["agent_id=?","status='queued'","(available_at IS NULL OR available_at<=?)"];values=[agent_id,now]
        if project_id:clauses.append("project_id=?");values.append(project_id)
        row=con.execute("SELECT * FROM agent_work_queue WHERE "+" AND ".join(clauses)+" ORDER BY priority DESC,created_at ASC LIMIT 1",values).fetchone()
        if not row:return None
        blocked=_load(row["blocked_by_json"])
        if blocked:return None
        con.execute("UPDATE agent_work_queue SET status='claimed',claimed_at=?,updated_at=? WHERE queue_id=? AND status='queued'",(now,now,row["queue_id"]))
        row=con.execute("SELECT * FROM agent_work_queue WHERE queue_id=?",(row["queue_id"],)).fetchone()
    return _queue(row)
def complete_work(queue_id:str,*,status:str="completed",database_path:str|None=None)->dict[str,object]:
    if status not in {"completed","blocked","cancelled"}:raise ValueError("unsupported queue completion status")
    _ensure(database_path);now=_now()
    with db.connect(database_path) as con:
        con.execute("UPDATE agent_work_queue SET status=?,completed_at=?,updated_at=? WHERE queue_id=?",(status,now,now,queue_id))
        row=con.execute("SELECT * FROM agent_work_queue WHERE queue_id=?",(queue_id,)).fetchone()
    if not row:raise KeyError(queue_id)
    return _queue(row)

def schedule_ready_tasks(*,project_id:str|None=None,limit:int=100,database_path:str|None=None)->list[dict[str,object]]:
    tasks=store.list_tasks(project_id=project_id,limit=min(max(int(limit),1),500),database_path=database_path); ready=[]
    project_priorities: dict[str, int] = {}
    if project_id is None:
        _ensure(database_path)
        with db.connect(database_path) as con:
            project_priorities = {
                str(row["id"]): int(row["priority"] or 50)
                for row in con.execute("SELECT id, priority FROM projects").fetchall()
            }
        tasks.sort(
            key=lambda item: (
                -project_priorities.get(str(item["project_id"]), 50),
                -int(item.get("priority") or 0),
                str(item.get("created_at") or ""),
            )
        )
    for task in tasks:
        if task["state"] not in {"pending","blocked","failed"}:continue
        if bool(task.get("writer")) and task.get("scope") and not store.resources_available(
            task["scope"], str(task["id"]), database_path=database_path
        ):
            continue
        dependencies=store.list_dependencies(str(task["id"]),database_path=database_path)
        if any((store.get_task(str(item["depends_on_task_id"]),database_path=database_path) or {}).get("state")!="completed" for item in dependencies):continue
        try: updated=store.transition(str(task["id"]),TaskState.READY,database_path=database_path)
        except (KeyError,ValueError):continue
        agent=str(updated.get("assigned_agent") or updated.get("role") or "supervisor")
        ready.append(enqueue_work(agent,str(updated["project_id"]),"task",str(updated["id"]),task_id=str(updated["id"]),priority=int(updated.get("priority") or 50),database_path=database_path))
    return ready

def sync_project(project_id:str,*,database_path:str|None=None)->dict[str,object]:
    project=get_project_state(project_id,database_path=database_path)
    if not project:raise KeyError(project_id)
    tasks=store.list_tasks(project_id=project_id,limit=500,database_path=database_path)
    counts={}
    for task in tasks:counts[str(task["state"])]=counts.get(str(task["state"]),0)+1
    blocked=[t for t in tasks if t["state"]=="blocked"]
    current=[t for t in tasks if t["state"] in {"assigned","running","review"}]
    requests=list_work_requests(project_id=project_id,status="open",database_path=database_path)
    return {"project":project,"task_counts":counts,"completed_work":[t["id"] for t in tasks if t["state"]=="completed"],
            "current_work":[{"task_id":t["id"],"title":t["title"],"role":t["role"]} for t in current],
            "blocked_tasks":[{"task_id":t["id"],"title":t["title"],"blocked_by":t["blocked_by"]} for t in blocked],
            "open_requests":requests,"dependencies":[d for t in tasks for d in store.list_dependencies(str(t["id"]),database_path=database_path)]}

def blackboard(*,project_id:str|None=None,database_path:str|None=None)->dict[str,object]:
    _ensure(database_path)
    with db.connect(database_path) as con:
        clauses=[];values=[]
        if project_id:clauses.append("id=?");values.append(project_id)
        where=" WHERE "+" AND ".join(clauses) if clauses else ""
        projects=[{"id":r["id"],"name":r["name"],"phase":_norm_phase(r["phase"] or "intake"),"priority":r["priority"],"workspace":r["workspace"]} for r in con.execute("SELECT id,name,phase,priority,workspace FROM projects"+where+" ORDER BY priority DESC,updated_at DESC",values).fetchall()]
        risk_where=("project_id=? AND status='open'" if project_id else "status='open'"); risk_values=[project_id] if project_id else []; risks=[_risk(r) for r in con.execute("SELECT * FROM project_risks WHERE "+risk_where+" ORDER BY created_at ASC",risk_values).fetchall()]
    project_ids=[p["id"] for p in projects]; tasks=[]
    for pid in project_ids:tasks.extend(store.list_tasks(project_id=str(pid),limit=500,database_path=database_path))
    reviews=[t for t in tasks if t["state"]=="review"]; failed=[t for t in tasks if t["state"]=="failed"]
    decisions=[]
    for pid in project_ids:decisions.extend(list_decisions(project_id=str(pid),database_path=database_path))
    requests=[]
    for pid in project_ids:requests.extend(list_work_requests(project_id=str(pid),status="open",database_path=database_path))
    return {"active_projects":[p for p in projects if p["phase"] not in (_TERMINAL | {ProjectPhase.PAUSED.value, ProjectPhase.FAILED.value})],
            "current_objectives":[{"project_id":p["id"],"name":p["name"],"phase":p["phase"]} for p in projects],
            "project_phases":{p["id"]:p["phase"] for p in projects},"open_risks":risks,
            "blockers":[t for t in tasks if t["state"] in {"blocked","waiting"}],
            "important_decisions":decisions,"failed_tests":[t for t in failed if str(t.get("role"))=="tester" or "test" in str(t.get("title","")).lower()],
            "open_reviews":reviews,"pending_questions":requests,"release_status":{p["id"]:p["phase"] for p in projects}}


class ProjectManager:
    """Delivery coordinator for milestones, gates, dependencies and status.

    Technical implementation remains delegated to the Engineering Manager and
    specialist agents; this service owns project delivery state and evidence.
    """

    ROLE = "project_manager"

    def __init__(self, *, database_path: str | None = None) -> None:
        self.database_path = database_path

    def status(self, project_id: str) -> dict[str, object]:
        return sync_project(project_id, database_path=self.database_path)

    def advance(
        self,
        project_id: str,
        target: ProjectPhase | str,
        *,
        evidence: Iterable[object] = (),
        reason: str = "",
    ) -> dict[str, object]:
        return transition_project_phase(
            project_id,
            target,
            actor_role=self.ROLE,
            evidence=evidence,
            reason=reason,
            database_path=self.database_path,
        )

    def add_milestone(
        self,
        project_id: str,
        title: str,
        *,
        description: str = "",
        due_at: str | None = None,
        deliverables: Iterable[object] = (),
        dependencies: Iterable[object] = (),
    ) -> dict[str, object]:
        return create_milestone(
            project_id,
            title,
            description=description,
            due_at=due_at,
            deliverables=deliverables,
            dependencies=dependencies,
            database_path=self.database_path,
        )

    def add_risk(
        self,
        project_id: str,
        title: str,
        *,
        severity: str = "medium",
        mitigation: str = "",
        owner: str | None = None,
    ) -> dict[str, object]:
        return create_risk(
            project_id,
            title,
            severity=severity,
            mitigation=mitigation,
            owner=owner,
            database_path=self.database_path,
        )

    def schedule(self, *, project_id: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        return schedule_ready_tasks(
            project_id=project_id,
            limit=limit,
            database_path=self.database_path,
        )

    def report(self, *, project_id: str | None = None) -> dict[str, object]:
        return blackboard(project_id=project_id, database_path=self.database_path)




