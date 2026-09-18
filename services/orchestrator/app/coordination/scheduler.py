from __future__ import annotations
from collections import defaultdict
from . import store
from .models import TaskState
class DependencyScheduler:
    def __init__(self, database_path: str | None=None, *, max_readers: int=4):
        self.database_path=database_path; self.max_readers=max(1,int(max_readers))
    def refresh(self, *, run_id: str | None=None, project_id: str | None=None) -> list[dict[str,object]]:
        tasks=store.list_tasks(run_id=run_id,project_id=project_id,limit=500,database_path=self.database_path); by_id={str(t["id"]):t for t in tasks}; changed=[]
        for task in tasks:
            state=str(task["state"]); deps=[str(d) for d in task["dependencies"]]
            if state not in {"pending","waiting","blocked","failed"}: continue
            missing=[d for d in deps if d not in by_id or str(by_id[d]["state"]) not in {"completed"}]
            terminal=[d for d in deps if d in by_id and str(by_id[d]["state"]) in {"failed","cancelled"}]
            if terminal and state!="blocked":
                changed.append(store.transition(str(task["id"]),TaskState.BLOCKED,failure_reason="Dependency failed: "+",".join(terminal),database_path=self.database_path))
            elif not missing and state in {"pending","waiting","blocked","failed"} and int(task["retry_count"])<=int(task["max_retries"]):
                changed.append(store.transition(str(task["id"]),TaskState.READY,database_path=self.database_path))
        return changed
    def ready_batches(self, *, run_id: str | None=None, project_id: str | None=None) -> list[list[dict[str,object]]]:
        self.refresh(run_id=run_id,project_id=project_id)
        ready=store.list_tasks(run_id=run_id,project_id=project_id,states=(TaskState.READY.value,),limit=500,database_path=self.database_path)
        batches:list[list[dict[str,object]]]=[]; readers=[]; writers=[]
        for task in ready:
            if task["writer"] or task["scope"] and any(set(task["scope"]) & set(other["scope"]) for other in writers):
                writers.append(task)
            elif all(not(set(task["scope"]) & set(other["scope"])) for other in writers+readers):
                readers.append(task)
            if len(readers)>=self.max_readers:
                batches.append(readers); readers=[]
        if readers: batches.append(readers)
        if writers: batches.extend([[task] for task in writers])
        return batches
    def assign(self, task_id: str, agent_id: str) -> dict[str,object]:
        return store.transition(task_id,TaskState.ASSIGNED,assigned_agent=agent_id,database_path=self.database_path)
    def start(self, task_id: str) -> dict[str,object]:
        task=store.get_task(task_id,database_path=self.database_path)
        if not task: raise KeyError(task_id)
        if task["writer"]:
            for resource in task["scope"]:
                if not store.acquire_lock(str(resource),task_id,str(task["role"]),database_path=self.database_path): raise RuntimeError("writer resource is locked")
        return store.transition(task_id,TaskState.RUNNING,database_path=self.database_path)
    def finish(self, task_id: str, *, success: bool, result: str="", error: str|None=None) -> dict[str,object]:
        state=TaskState.REVIEW if success else TaskState.FAILED
        return store.transition(task_id,state,failure_reason=None if success else (error or result),database_path=self.database_path)
    def complete_review(self, task_id: str, approved: bool, reason: str|None=None) -> dict[str,object]:
        return store.transition(task_id,TaskState.COMPLETED if approved else TaskState.FAILED,failure_reason=reason,database_path=self.database_path)
