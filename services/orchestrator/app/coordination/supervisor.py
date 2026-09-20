from __future__ import annotations

import json
import logging
from uuid import uuid4

from app.db import connect, initialize_database, utc_now
from app.memory import MemoryStore
from app.organization.director import TeamPlanner
from app.organization.store import get_project_team_plan, save_project_organization, update_team_plan_assignments

from . import store
from .bus import DiscussionController, HandoffProtocol, MessageBus
from .models import AgentHandoff, CoordinationTask, MessageType, TaskState
from .roles import get_role_contract

logger = logging.getLogger(__name__)


class Supervisor:
    """Engineering-manager coordinator for a persisted multi-agent run."""

    def __init__(self, database_path: str | None = None, *, max_retries: int = 2):
        self.database_path = database_path
        self.max_retries = max(0, int(max_retries))
        self.bus = MessageBus(database_path)
        self.discussion = DiscussionController(self.bus)
        self.handoffs = HandoffProtocol(database_path)
        self.memory = MemoryStore(database_path)

    def _run(self, project_id: str, objective: str, run_id: str | None = None) -> str:
        run_id = run_id or str(uuid4())
        now = utc_now()
        with connect(self.database_path) as database:
            database.execute(
                "INSERT OR IGNORE INTO autonomy_runs(id,project_id,goal,requested_cycles,completed_cycles,status,task_ids_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, project_id, objective[:20000], 1, 0, "running", "[]", now, now),
            )
        return run_id

    def start_objective(
        self,
        *,
        project_id: str,
        objective: str,
        run_id: str | None = None,
    ) -> dict[str, object]:
        objective = str(objective or "").strip()
        if not objective:
            raise ValueError("objective is required")
        initialize_database(self.database_path)
        team_plan = get_project_team_plan(project_id, database_path=self.database_path)
        if not team_plan or not team_plan.get("selected_roles"):
            generated = TeamPlanner().plan(project_id, objective)
            save_project_organization(
                generated,
                database_path=self.database_path,
                persist_team_plan=True,
            )
            team_plan = {
                **generated.as_dict(),
                "assigned_tasks": {},
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        if run_id is None:
            with connect(self.database_path) as database:
                existing_run = database.execute(
                    "SELECT id FROM autonomy_runs WHERE project_id = ? AND goal = ? AND status IN ('running', 'blocked', 'waiting') ORDER BY created_at DESC LIMIT 1",
                    (project_id, objective[:20000]),
                ).fetchone()
            run_id = str(existing_run["id"]) if existing_run else self._run(project_id, objective)
        else:
            self._run(project_id, objective, run_id)
        existing_tasks = store.list_tasks(
            run_id=run_id,
            project_id=project_id,
            limit=500,
            database_path=self.database_path,
        )
        if existing_tasks:
            return {
                "run_id": run_id,
                "project_id": project_id,
                "objective": objective,
                "team_plan": team_plan,
                "tasks": existing_tasks,
                "experience": self.memory.retrieve(
                    project_id=project_id, query=objective, role="supervisor",
                    task_type="objective", run_id=run_id, limit=8,
                    include_candidate=True,
                ),
                "state": "running",
                "resumed": True,
            }
        selected_roles = tuple(str(role) for role in team_plan.get("selected_roles", ()))
        reasons = team_plan.get("role_reasons", {})
        responsibilities = team_plan.get("role_responsibilities", {})
        if not isinstance(reasons, dict):
            reasons = {}
        if not isinstance(responsibilities, dict):
            responsibilities = {}
        specs = TeamPlanner().build_execution_specs(selected_roles)
        made: dict[str, str] = {}
        created: list[dict[str, object]] = []
        assignments: dict[str, list[str]] = {}
        for role, title, dependency_roles in specs:
            contract = get_role_contract(role)
            dependencies = tuple(made[item] for item in dependency_roles if item in made)
            reason = str(reasons.get(role) or "Selected by the persisted execution team plan.")
            responsibility = str(responsibilities.get(role) or contract.purpose)
            writer = contract.write_permission.value != "read_only"
            task = CoordinationTask(
                project_id=project_id, run_id=run_id, title=title,
                description=f"{title} for objective: {objective}. Team-plan reason: {reason}",
                role=role, dependencies=dependencies,
                inputs={"team_plan_id": team_plan.get("plan_id"), "team_plan_role": role, "selection_reason": reason, "responsibility": responsibility},
                expected_outputs=contract.output_contract,
                acceptance_criteria=("Produce evidence.", f"Complete responsibility: {responsibility}", "Hand off to the next selected role."),
                max_retries=self.max_retries,
                scope=(
                    (f"project:{project_id}:{role}" if role in {"backend", "frontend", "devops", "docs"} else f"project:{project_id}:shared",)
                    if writer
                    else (f"project:{project_id}:read:{role}",)
                ),
                writer=writer,
            )
            created_task = store.create_task(task, database_path=self.database_path)
            created.append(created_task)
            made[role] = task.id
            assignments.setdefault(role, []).append(task.id)
        update_team_plan_assignments(project_id, assignments, database_path=self.database_path)
        with connect(self.database_path) as database:
            database.execute("UPDATE autonomy_runs SET task_ids_json=?,updated_at=? WHERE id=?", (json.dumps([str(item["id"]) for item in created]), utc_now(), run_id))
        self.bus.publish(
            sender_role="supervisor", message_type=MessageType.STATUS,
            subject="Objective accepted", body=objective, run_id=run_id,
            project_id=project_id, references=[str(team_plan.get("plan_id") or "")],
        )
        return {
            "run_id": run_id, "project_id": project_id, "objective": objective,
            "team_plan": get_project_team_plan(project_id, database_path=self.database_path) or team_plan,
            "tasks": created,
            "experience": self.memory.retrieve(
                project_id=project_id, query=objective, role="supervisor",
                task_type="objective", run_id=run_id, limit=8, include_candidate=True,
            ),
            "state": "running", "resumed": False,
        }

    def next_ready(self, *, run_id: str, project_id: str | None = None) -> list[list[dict[str, object]]]:
        from .scheduler import DependencyScheduler

        return DependencyScheduler(self.database_path).ready_batches(run_id=run_id, project_id=project_id)

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

    def _release_locks(self, task: dict[str, object]) -> None:
        if task.get("writer"):
            for resource in task.get("scope", ()):
                store.release_lock(str(resource), str(task["id"]), database_path=self.database_path)

    def _record_experience(
        self,
        task: dict[str, object],
        summary: str,
        *,
        success: bool,
        evidence: list[str] = (),
        failure_reason: str | None = None,
    ) -> None:
        role = str(task.get("role") or "implementer")
        contract = get_role_contract(role)
        references = [{"type": "result", "summary": summary}]
        references.extend({"type": "evidence", "summary": item} for item in evidence[:20])
        try:
            self.memory.extract_task_experience(
                project_id=str(task.get("project_id") or "") or None,
                run_id=str(task.get("run_id") or "") or None,
                task_id=str(task.get("id") or "") or None,
                role=role,
                task_type=str(task.get("title") or role),
                summary=summary,
                evidence=references,
                failure_reason=failure_reason,
                retry_count=int(task.get("retry_count") or 0),
                model_profile=contract.default_model_profile,
                tests_passed=success if role in {"tester", "release_verifier"} else None,
                review_accepted=success if role in {"reviewer", "release_verifier"} else None,
                success=success,
            )
        except Exception:
            logger.exception("Failed to record engineering experience", extra={"task_id": task.get("id")})
    def record_result(self, task_id: str, *, summary: str, evidence: list[str] = (), approved: bool = True) -> dict[str, object]:
        task = self._ensure_running(task_id)
        state = TaskState.COMPLETED if approved else TaskState.REVIEW
        result = store.transition(task_id, state, database_path=self.database_path)
        if approved:
            self._release_locks(result)
        self.bus.publish(
            sender_role=str(task["role"]),
            message_type=MessageType.RESULT,
            subject=str(task["title"]),
            body=summary,
            run_id=str(task["run_id"] or ""),
            project_id=str(task["project_id"]),
            task_id=task_id,
            references=evidence,
        )
        self._record_experience(task, summary, success=approved, evidence=evidence, failure_reason=None if approved else summary)
        from .scheduler import DependencyScheduler

        DependencyScheduler(self.database_path).refresh(run_id=str(task["run_id"] or ""))
        self._refresh_run(str(task["run_id"] or ""))
        return result

    def record_failure(self, task_id: str, *, reason: str) -> dict[str, object]:
        task = self._ensure_running(task_id)
        result = store.transition(task_id, TaskState.FAILED, failure_reason=reason, database_path=self.database_path)
        self._release_locks(result)
        self.bus.publish(
            sender_role=str(task["role"]),
            message_type=MessageType.BLOCKER,
            subject=str(task["title"]),
            body=reason,
            run_id=str(task["run_id"] or ""),
            project_id=str(task["project_id"]),
            task_id=task_id,
        )
        self._record_experience(task, reason, success=False, failure_reason=reason)
        from .scheduler import DependencyScheduler

        DependencyScheduler(self.database_path).refresh(run_id=str(task["run_id"] or ""))
        self._refresh_run(str(task["run_id"] or ""))
        return result

    def request_revision(self, task_id: str, *, reason: str) -> dict[str, object]:
        task = store.get_task(task_id, database_path=self.database_path)
        if not task:
            raise KeyError(task_id)
        result = store.transition(task_id, TaskState.FAILED, failure_reason=reason, database_path=self.database_path)
        self._release_locks(result)
        self.bus.publish(
            sender_role="reviewer",
            message_type=MessageType.REVISION_REQUEST,
            subject="Revision requested",
            body=reason,
            run_id=str(task["run_id"] or ""),
            project_id=str(task["project_id"]),
            task_id=task_id,
        )
        self._record_experience(task, reason, success=False, failure_reason=reason)
        from .scheduler import DependencyScheduler

        DependencyScheduler(self.database_path).refresh(run_id=str(task["run_id"] or ""))
        return result

    def resolve_disagreement(self, *, run_id: str, project_id: str, subject: str, decision: str, evidence: list[str] = (), task_id: str | None = None) -> dict[str, object]:
        return self.discussion.resolve(run_id=run_id, project_id=project_id, subject=subject, decision=decision, evidence=evidence, task_id=task_id)

    def submit_handoff(self, handoff: AgentHandoff) -> dict[str, object]:
        return self.handoffs.submit(handoff)

    def _refresh_run(self, run_id: str) -> None:
        if not run_id:
            return
        tasks = store.list_tasks(run_id=run_id, limit=500, database_path=self.database_path)
        terminal_failed = any(str(item["state"]) == TaskState.FAILED.value and int(item["retry_count"]) > int(item["max_retries"]) for item in tasks)
        blocked = any(str(item["state"]) == TaskState.BLOCKED.value for item in tasks)
        status = "completed" if tasks and all(str(item["state"]) == TaskState.COMPLETED.value for item in tasks) else "failed" if terminal_failed else "blocked" if blocked else "running"
        with connect(self.database_path) as database:
            database.execute("UPDATE autonomy_runs SET status=?,completed_cycles=?,updated_at=? WHERE id=?", (status, 1 if status == "completed" else 0, utc_now(), run_id))

    def status(self, run_id: str) -> dict[str, object]:
        tasks = store.list_tasks(run_id=run_id, limit=500, database_path=self.database_path)
        messages = self.bus.relevant(run_id=run_id, limit=100)
        handoffs = self.handoffs.list(run_id=run_id, limit=100)
        states = {state.value: sum(1 for item in tasks if str(item["state"]) == state.value) for state in TaskState}
        with connect(self.database_path) as database:
            run_row = database.execute("SELECT status,project_id FROM autonomy_runs WHERE id=?", (run_id,)).fetchone()
        project_id = run_row["project_id"] if run_row else None
        return {"run_id": run_id, "run_status": run_row["status"] if run_row else "unknown", "tasks": tasks, "states": states, "messages": messages, "handoffs": handoffs, "experience": self.memory.retrieve(project_id=project_id, query="", run_id=run_id, limit=12, include_candidate=True), "performance": self.memory.performance(limit=20), "complete": bool(tasks) and states[TaskState.COMPLETED.value] == len(tasks), "blocked": states[TaskState.BLOCKED.value], "failed": states[TaskState.FAILED.value]}




