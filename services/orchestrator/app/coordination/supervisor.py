from __future__ import annotations
import json
from uuid import uuid4
from app.db import connect, initialize_database, utc_now
from . import store
from .bus import DiscussionController, HandoffProtocol, MessageBus
from .models import AgentHandoff, MessageType, CoordinationTask, TaskState
from .roles import get_role_contract, resolve_role
class Supervisor:
    def __init__(self,database_path: str|None=None, *, max_retries: int=2):
        self.database_path=database_path; self.max_retries=max(0,int(max_retries)); self.bus=MessageBus(database_path); self.discussion=DiscussionController(self.bus); self.handoffs=HandoffProtocol(database_path)
    def _run(self, project_id: str, objective: str) -> str:
        run_id=str(uuid4()); now=utc_now()
        with connect(self.database_path) as db:
            db.execute("INSERT INTO autonomy_runs(id,project_id,goal,requested_cycles,completed_cycles,status,task_ids_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",(run_id,project_id,objective[:20000],1,0,"running","[]",now,now))
        return run_id
    def start_objective(self, *, project_id: str, objective: str, run_id: str|None=None) -> dict[str,object]:
        if not str(objective or "").strip(): raise ValueError("objective is required")
        initialize_database(self.database_path)
        run_id=run_id or self._run(project_id,objective)
        specs=[("requirements","Clarify requirements",()),("planner","Create task graph",("requirements",)),("architect","Define architecture",("planner",)),("backend","Implement backend scope",("architect",)),("frontend","Implement frontend scope",("architect",)),("implementer","Implement shared scope",("architect",)),("integration","Integrate compatible changes",("backend","frontend","implementer")),("tester","Run tests",("integration",)),("reviewer","Review implementation",("tester",)),("release_verifier","Verify release",("reviewer",))]
        made:dict[str,str]={}
        created:list[dict[str,object]]=[]
        for role,title,dependency_roles in specs:
            dependencies=tuple(made[d] for d in dependency_roles)
            contract=get_role_contract(role)
            task=CoordinationTask(project_id=project_id,run_id=run_id,title=title,description=f"{title} for objective: {objective}",role=role,dependencies=dependencies,expected_outputs=contract.output_contract,acceptance_criteria=("Produce evidence.", "Hand off to the next role."),max_retries=self.max_retries,scope=(role,),writer=contract.write_permission.value!="read_only")
            created.append(store.create_task(task,database_path=self.database_path)); made[role]=task.id
        with connect(self.database_path) as db:
            db.execute("UPDATE autonomy_runs SET task_ids_json=?,updated_at=? WHERE id=?",(json.dumps([str(item["id"]) for item in created]),utc_now(),run_id))
        self.bus.publish(sender_role="supervisor",message_type=MessageType.STATUS,subject="Objective accepted",body=objective,run_id=run_id,project_id=project_id)
        return {"run_id":run_id,"project_id":project_id,"objective":objective,"tasks":created,"state":"running"}
    def next_ready(self, *, run_id: str, project_id: str|None=None) -> list[list[dict[str,object]]]:
        from .scheduler import DependencyScheduler
        return DependencyScheduler(self.database_path).ready_batches(run_id=run_id,project_id=project_id)
    def _ensure_running(self, task_id: str) -> dict[str, object]:
        from .scheduler import DependencyScheduler
        task = store.get_task(task_id, database_path=self.database_path)
        if not task:
            raise KeyError(task_id)
        scheduler = DependencyScheduler(self.database_path)
        if str(task["state"]) == TaskState.PENDING.value:
            scheduler.refresh(run_id=str(task["run_id"] or ""))
            task = store.get_task(task_id, database_path=self.database_path)
        if not task:
            raise KeyError(task_id)
        state = str(task["state"])
        if state == TaskState.READY.value:
            scheduler.assign(task_id, str(task["role"]))
            task = store.get_task(task_id, database_path=self.database_path)
            state = str(task["state"]) if task else ""
        if state == TaskState.ASSIGNED.value:
            task = scheduler.start(task_id)
            state = str(task["state"])
        elif state == TaskState.WAITING.value:
            task = store.transition(task_id, TaskState.RUNNING, database_path=self.database_path)
            state = str(task["state"])
        if state != TaskState.RUNNING.value:
            raise ValueError(f"task {task_id} is not runnable: {state}")
        return task

    def record_result(self, task_id: str, *, summary: str, evidence: list[str] = (), approved: bool = True) -> dict[str, object]:
        task = self._ensure_running(task_id)
        state = TaskState.COMPLETED if approved else TaskState.REVIEW
        result = store.transition(task_id, state, database_path=self.database_path)
        self.bus.publish(sender_role=str(task["role"]), message_type=MessageType.RESULT, subject=str(task["title"]), body=summary, run_id=str(task["run_id"] or ""), project_id=str(task["project_id"]), task_id=task_id, references=evidence)
        self._refresh_run(str(task["run_id"] or ""))
        return result

    def record_failure(self, task_id: str, *, reason: str) -> dict[str, object]:
        task=self._ensure_running(task_id)
        result=store.transition(task_id,TaskState.FAILED,failure_reason=reason,database_path=self.database_path)
        self.bus.publish(sender_role=str(task["role"]),message_type=MessageType.BLOCKER,subject=str(task["title"]),body=reason,run_id=str(task["run_id"] or ""),project_id=str(task["project_id"]),task_id=task_id)
        from .scheduler import DependencyScheduler
        DependencyScheduler(self.database_path).refresh(run_id=str(task["run_id"] or ""))
        self._refresh_run(str(task["run_id"] or ""))
        return result
    def request_revision(self, task_id: str, *, reason: str) -> dict[str,object]:
        task=store.get_task(task_id,database_path=self.database_path)
        if not task: raise KeyError(task_id)
        result=store.transition(task_id,TaskState.FAILED,failure_reason=reason,database_path=self.database_path)
        self.bus.publish(sender_role="reviewer",message_type=MessageType.REVISION_REQUEST,subject="Revision requested",body=reason,run_id=str(task["run_id"] or ""),project_id=str(task["project_id"]),task_id=task_id)
        from .scheduler import DependencyScheduler
        DependencyScheduler(self.database_path).refresh(run_id=str(task["run_id"] or ""))
        return result
    def resolve_disagreement(self, *, run_id: str, project_id: str, subject: str, decision: str, evidence: list[str]=(), task_id: str|None=None) -> dict[str,object]:
        return self.discussion.resolve(run_id=run_id,project_id=project_id,subject=subject,decision=decision,evidence=evidence,task_id=task_id)
    def submit_handoff(self, handoff: AgentHandoff) -> dict[str,object]: return self.handoffs.submit(handoff)
    def _refresh_run(self, run_id: str) -> None:
        if not run_id: return
        tasks=store.list_tasks(run_id=run_id,limit=500,database_path=self.database_path)
        status="completed" if tasks and all(str(t["state"])=="completed" for t in tasks) else "failed" if any(str(t["state"])=="failed" and int(t["retry_count"])>int(t["max_retries"]) for t in tasks) else "running"
        with connect(self.database_path) as db: db.execute("UPDATE autonomy_runs SET status=?,completed_cycles=?,updated_at=? WHERE id=?",(status,1 if status=="completed" else 0,utc_now(),run_id))
    def status(self, run_id: str) -> dict[str,object]:
        tasks=store.list_tasks(run_id=run_id,limit=500,database_path=self.database_path); messages=self.bus.relevant(run_id=run_id,limit=100); handoffs=self.handoffs.list(run_id=run_id,limit=100)
        states={state:sum(1 for t in tasks if str(t["state"])==state) for state in [item.value for item in TaskState]}
        return {"run_id":run_id,"tasks":tasks,"states":states,"messages":messages,"handoffs":handoffs,"complete":bool(tasks) and states["completed"]==len(tasks),"blocked":states["blocked"],"failed":states["failed"]}






