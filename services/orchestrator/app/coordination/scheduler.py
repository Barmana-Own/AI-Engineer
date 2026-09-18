from __future__ import annotations

from . import store
from .models import TaskState


class DependencyScheduler:
    def __init__(self, database_path: str | None = None, *, max_readers: int = 4):
        self.database_path = database_path
        self.max_readers = max(1, int(max_readers))

    def refresh(self, *, run_id: str | None = None, project_id: str | None = None) -> list[dict[str, object]]:
        tasks = store.list_tasks(run_id=run_id, project_id=project_id, limit=500, database_path=self.database_path)
        by_id = {str(task["id"]): task for task in tasks}
        changed: list[dict[str, object]] = []
        for task in tasks:
            state = str(task["state"])
            if state not in {TaskState.PENDING.value, TaskState.WAITING.value, TaskState.BLOCKED.value, TaskState.FAILED.value}:
                continue
            dependencies = [str(item) for item in task["dependencies"]]
            missing = [dependency for dependency in dependencies if dependency not in by_id or str(by_id[dependency]["state"]) != TaskState.COMPLETED.value]
            terminal = [dependency for dependency in dependencies if dependency in by_id and str(by_id[dependency]["state"]) in {TaskState.FAILED.value, TaskState.CANCELLED.value, TaskState.BLOCKED.value}]
            if terminal and state != TaskState.BLOCKED.value:
                changed.append(store.transition(str(task["id"]), TaskState.BLOCKED, failure_reason="Dependency failed: " + ",".join(terminal), database_path=self.database_path))
            elif not missing and int(task["retry_count"]) <= int(task["max_retries"]):
                changed.append(store.transition(str(task["id"]), TaskState.READY, database_path=self.database_path))
        return changed

    def ready_batches(self, *, run_id: str | None = None, project_id: str | None = None) -> list[list[dict[str, object]]]:
        self.refresh(run_id=run_id, project_id=project_id)
        ready = store.list_tasks(run_id=run_id, project_id=project_id, states=(TaskState.READY.value,), limit=500, database_path=self.database_path)
        batches: list[list[dict[str, object]]] = []
        readers: list[dict[str, object]] = []
        writers: list[dict[str, object]] = []
        for task in ready:
            if task["writer"]:
                writers.append(task)
            elif all(not (set(task["scope"]) & set(other["scope"])) for other in writers + readers):
                readers.append(task)
            if len(readers) >= self.max_readers:
                batches.append(readers)
                readers = []
        if readers:
            batches.append(readers)
        batches.extend([[task] for task in writers])
        return batches

    def assign(self, task_id: str, agent_id: str) -> dict[str, object]:
        return store.transition(task_id, TaskState.ASSIGNED, assigned_agent=agent_id, database_path=self.database_path)

    def start(self, task_id: str) -> dict[str, object]:
        task = store.get_task(task_id, database_path=self.database_path)
        if not task:
            raise KeyError(task_id)
        acquired: list[str] = []
        try:
            if task["writer"]:
                for resource in task["scope"]:
                    if not store.acquire_lock(str(resource), task_id, str(task["role"]), database_path=self.database_path):
                        raise RuntimeError("writer resource is locked")
                    acquired.append(str(resource))
            return store.transition(task_id, TaskState.RUNNING, database_path=self.database_path)
        except Exception:
            for resource in acquired:
                store.release_lock(resource, task_id, database_path=self.database_path)
            raise

    def _release_task_locks(self, task_id: str, task: dict[str, object] | None = None) -> None:
        task = task or store.get_task(task_id, database_path=self.database_path)
        if task and task["writer"]:
            for resource in task["scope"]:
                store.release_lock(str(resource), task_id, database_path=self.database_path)

    def finish(self, task_id: str, *, success: bool, result: str = "", error: str | None = None) -> dict[str, object]:
        state = TaskState.REVIEW if success else TaskState.FAILED
        updated = store.transition(task_id, state, failure_reason=None if success else (error or result), database_path=self.database_path)
        if not success:
            self._release_task_locks(task_id, updated)
        return updated

    def complete_review(self, task_id: str, approved: bool, reason: str | None = None) -> dict[str, object]:
        updated = store.transition(task_id, TaskState.COMPLETED if approved else TaskState.FAILED, failure_reason=reason, database_path=self.database_path)
        self._release_task_locks(task_id, updated)
        return updated
