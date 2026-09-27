from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import MessageBus
from app.coordination.models import AgentHandoff, CoordinationTask, MessageType, TaskState
from app.coordination.project_management import (
    create_milestone as persist_milestone,
    create_risk as persist_risk,
    get_project_state,
    list_milestones as persisted_milestones,
    list_risks,
    list_work_requests,
    schedule_ready_tasks,
)
from app.coordination.scheduler import DependencyScheduler
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _items(values: Iterable[object] | None, *, limit: int = 100, max_chars: int = 1000) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for value in values or ():
        cleaned = _clean(value, max_chars=max_chars)
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) >= limit:
            break
    return tuple(result)


@dataclass(frozen=True)
class DeliverablePlan:
    """A deliverable that becomes one task in the existing task DAG."""

    title: str
    description: str = ""
    role: str = "implementer"
    acceptance_criteria: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    priority: int = 50
    writer: bool = False
    scope: tuple[str, ...] = ()
    assigned_agent: str | None = None
    task_id: str | None = None

    def __post_init__(self) -> None:
        title = _clean(self.title, max_chars=500)
        if not title:
            raise ValueError("deliverable title is required")
        if not _clean(self.role, max_chars=128):
            raise ValueError("deliverable role is required")
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "description", _clean(self.description, max_chars=20_000))
        object.__setattr__(self, "role", _clean(self.role, max_chars=128))
        object.__setattr__(self, "acceptance_criteria", _items(self.acceptance_criteria))
        object.__setattr__(self, "dependencies", _items(self.dependencies, max_chars=128))
        object.__setattr__(self, "scope", _items(self.scope, max_chars=500))
        object.__setattr__(self, "priority", max(0, min(100, int(self.priority))))
        if self.assigned_agent is not None:
            object.__setattr__(self, "assigned_agent", _clean(self.assigned_agent, max_chars=128) or None)

    @classmethod
    def from_value(cls, value: object) -> "DeliverablePlan":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(title=value)
        if not isinstance(value, Mapping):
            raise TypeError("deliverables must be strings, mappings, or DeliverablePlan values")
        title = value.get("title") or value.get("name") or value.get("deliverable")
        return cls(
            title=str(title or ""),
            description=str(value.get("description") or ""),
            role=str(value.get("role") or value.get("owner_role") or value.get("assigned_role") or "implementer"),
            acceptance_criteria=tuple(value.get("acceptance_criteria") or ()),
            dependencies=tuple(value.get("dependencies") or ()),
            priority=int(value.get("priority", 50)),
            writer=bool(value.get("writer", False)),
            scope=tuple(value.get("scope") or ()),
            assigned_agent=str(value.get("assigned_agent")) if value.get("assigned_agent") else None,
            task_id=str(value.get("task_id")) if value.get("task_id") else None,
        )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MilestonePlan:
    milestone_id: str
    project_id: str
    title: str
    description: str
    due_at: str | None
    task_id: str
    deliverables: tuple[DeliverablePlan, ...]
    dependencies: tuple[str, ...] = ()
    scheduled_queue_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "milestone_id": self.milestone_id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "due_at": self.due_at,
            "task_id": self.task_id,
            "deliverables": [item.as_dict() for item in self.deliverables],
            "task_ids": [item.task_id for item in self.deliverables if item.task_id],
            "dependencies": list(self.dependencies),
            "scheduled_queue_ids": list(self.scheduled_queue_ids),
        }


@dataclass(frozen=True)
class ScopeEscalation:
    escalation_id: str
    project_id: str
    reason: str
    requested_change: str
    affected_task_ids: tuple[str, ...]
    target_role: str
    requires_human_owner_approval: bool = True
    commitment_made: bool = False
    status: str = "pending_owner_approval"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectStatusReport:
    project_id: str
    project: Mapping[str, object]
    task_counts: Mapping[str, int]
    completed_work: tuple[dict[str, object], ...]
    current_work: tuple[dict[str, object], ...]
    pending_work: tuple[dict[str, object], ...]
    blocked_tasks: tuple[dict[str, object], ...]
    dependencies: tuple[dict[str, object], ...]
    milestones: tuple[dict[str, object], ...]
    risks: tuple[dict[str, object], ...]
    open_requests: tuple[dict[str, object], ...]
    scope_escalations: tuple[dict[str, object], ...]
    next_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["project"] = dict(self.project)
        return result


class ProjectManagerAgent:
    """Delivery coordinator layered on the existing task DAG and work queue.

    The Project Manager owns delivery sequencing, milestones, status and
    escalation. It never writes workspace files or makes low-level design
    decisions; implementation and technical decisions remain delegated to the
    existing Engineering Manager and specialist roles.
    """

    ROLE = "project_manager"
    DISPLAY_NAME = "Project Manager"
    _HANDOFF_TARGETS = frozenset({"engineering_manager", "architect", "company_director", "supervisor"})

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-project-manager",
            display_name=self.DISPLAY_NAME,
            department=Department.PRODUCT,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _project(self, project_id: str) -> dict[str, object]:
        project = get_project_state(project_id, database_path=self.database_path)
        if not project:
            raise KeyError(f"Project not found: {project_id}")
        return project

    def _validate_task_ids(self, project_id: str, values: Iterable[object]) -> tuple[str, ...]:
        result: list[str] = []
        for value in values:
            task_id = str(value or "").strip()
            if not task_id or task_id in result:
                continue
            task = coordination_store.get_task(task_id, database_path=self.database_path)
            if not task:
                raise ValueError(f"Unknown dependency task: {task_id}")
            if str(task["project_id"]) != project_id:
                raise ValueError("Project Manager cannot mix task dependencies across projects")
            result.append(task_id)
        return tuple(result)

    def create_milestone(
        self,
        project_id: str,
        title: str,
        *,
        description: str = "",
        due_at: str | None = None,
        deliverables: Iterable[object] = (),
        dependencies: Iterable[object] = (),
        priority: int = 50,
        run_id: str | None = None,
    ) -> MilestonePlan:
        self.ensure_profile()
        self._project(project_id)
        clean_title = _clean(title, max_chars=500)
        if not clean_title:
            raise ValueError("milestone title is required")
        specs = tuple(DeliverablePlan.from_value(value) for value in deliverables)
        if not specs:
            raise ValueError("a milestone requires at least one deliverable")
        milestone_dependencies = self._validate_task_ids(project_id, dependencies)
        milestone_id = str(uuid4())
        parent = CoordinationTask(
            project_id=project_id,
            run_id=run_id,
            title=f"Milestone: {clean_title}",
            description=_clean(description, max_chars=20_000),
            role=self.ROLE,
            state=TaskState.PENDING,
            priority=max(0, min(100, int(priority))),
            dependencies=milestone_dependencies,
            inputs={"kind": "milestone", "milestone_id": milestone_id, "title": clean_title},
            expected_outputs=("milestone_status", "delivery_report"),
            acceptance_criteria=tuple(f"Deliverable completed: {item.title}" for item in specs),
            writer=False,
        )

        title_to_id: dict[str, str] = {}
        materialized: list[DeliverablePlan] = []
        for spec in specs:
            task_id = spec.task_id or str(uuid4())
            title_to_id[spec.title.casefold()] = task_id
            materialized.append(replace(spec, task_id=task_id))

        # Persist the existing milestone record and then create its DAG tasks.
        # The parent task's inputs provide a durable link back to this record;
        # deliverable JSON carries each child task id for restart-safe lookup.
        persisted_milestone = persist_milestone(
            project_id,
            clean_title,
            description=_clean(description, max_chars=10_000),
            due_at=_clean(due_at, max_chars=128) or None,
            deliverables=[item.as_dict() for item in materialized],
            dependencies=milestone_dependencies,
            milestone_id=milestone_id,
            database_path=self.database_path,
        )
        coordination_store.create_task(parent, database_path=self.database_path)
        pending_dependencies: list[tuple[str, tuple[str, ...]]] = []
        for spec in materialized:
            resolved_dependencies: list[str] = []
            for dependency in spec.dependencies:
                dependency_id = title_to_id.get(dependency.casefold(), dependency)
                if dependency_id == spec.task_id:
                    raise ValueError("A deliverable cannot depend on itself")
                if dependency_id not in title_to_id.values():
                    self._validate_task_ids(project_id, (dependency_id,))
                resolved_dependencies.append(dependency_id)
            task = CoordinationTask(
                id=str(spec.task_id),
                project_id=project_id,
                run_id=run_id,
                parent_task_id=parent.id,
                title=spec.title,
                description=spec.description,
                role=spec.role,
                assigned_agent=spec.assigned_agent,
                state=TaskState.PENDING,
                priority=spec.priority,
                dependencies=(),
                inputs={"kind": "deliverable", "milestone_id": milestone_id, "deliverable": spec.title},
                expected_outputs=("deliverable_artifact",),
                acceptance_criteria=spec.acceptance_criteria,
                scope=spec.scope,
                writer=spec.writer,
            )
            coordination_store.create_task(task, database_path=self.database_path)
            pending_dependencies.append((str(spec.task_id), tuple(resolved_dependencies)))

        # Add edges after all child nodes exist so a deliverable can depend on
        # a later sibling without violating the database foreign key.
        for task_id, dependencies in pending_dependencies:
            for dependency_id in dependencies:
                coordination_store.add_dependency(
                    task_id,
                    dependency_id,
                    database_path=self.database_path,
                )


        scheduled = schedule_ready_tasks(project_id=project_id, database_path=self.database_path)
        self.bus.publish(
            sender_role=self.ROLE,
            recipient_role="supervisor",
            message_type=MessageType.STATUS,
            subject=f"Milestone created: {clean_title}",
            body=json.dumps(
                {
                    "milestone": persisted_milestone,
                    "milestone_task_id": parent.id,
                    "deliverable_task_ids": [item.task_id for item in materialized],
                    "scheduled_queue_ids": [item.get("queue_id") for item in scheduled],
                },
                ensure_ascii=False,
            ),
            project_id=project_id,
            run_id=run_id,
            task_id=parent.id,
            topic="milestone",
        )
        return MilestonePlan(
            milestone_id=milestone_id,
            project_id=project_id,
            title=clean_title,
            description=_clean(description, max_chars=20_000),
            due_at=_clean(due_at, max_chars=128) or None,
            task_id=parent.id,
            deliverables=tuple(materialized),
            dependencies=milestone_dependencies,
            scheduled_queue_ids=tuple(str(item["queue_id"]) for item in scheduled if item.get("queue_id")),
        )

    add_milestone = create_milestone

    def add_dependency(self, task_id: str, dependency_task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(task_id, database_path=self.database_path)
        dependency = coordination_store.get_task(dependency_task_id, database_path=self.database_path)
        if not task or not dependency:
            raise KeyError(task_id if not task else dependency_task_id)
        if str(task["project_id"]) != str(dependency["project_id"]):
            raise ValueError("Dependencies must remain within one project")
        result = coordination_store.add_dependency(
            task_id,
            dependency_task_id,
            database_path=self.database_path,
        )
        schedule_ready_tasks(project_id=str(task["project_id"]), database_path=self.database_path)
        return result

    def dependencies(self, task_id: str | None = None) -> list[dict[str, str]]:
        return coordination_store.list_dependencies(task_id, database_path=self.database_path)

    def detect_blocked_tasks(self, project_id: str) -> list[dict[str, object]]:
        self._project(project_id)
        DependencyScheduler(self.database_path).refresh(project_id=project_id)
        tasks = coordination_store.list_tasks(project_id=project_id, limit=500, database_path=self.database_path)
        by_id = {str(item["id"]): item for item in tasks}
        blocked: list[dict[str, object]] = []
        for task in tasks:
            dependency_ids = [str(item) for item in task.get("dependencies", ())]
            unresolved = [item for item in dependency_ids if item not in by_id or by_id[item]["state"] != TaskState.COMPLETED.value]
            terminal = [
                item for item in unresolved
                if item in by_id and by_id[item]["state"] in {
                    TaskState.BLOCKED.value,
                    TaskState.FAILED.value,
                    TaskState.CANCELLED.value,
                }
            ]
            if task["state"] == TaskState.BLOCKED.value or terminal or (
                unresolved and task["state"] in {TaskState.PENDING.value, TaskState.WAITING.value}
            ):
                blocked.append(
                    {
                        "task_id": task["id"],
                        "title": task["title"],
                        "role": task["role"],
                        "state": task["state"],
                        "blocked_by": terminal or unresolved,
                        "reason": "dependency_failed" if terminal or str(task.get("failure_reason") or "").startswith("Dependency failed") else "waiting_for_dependency",
                        "failure_reason": task.get("failure_reason"),
                    }
                )
        return blocked

    def _milestone_status(self, project_id: str, tasks: Sequence[Mapping[str, object]]) -> tuple[dict[str, object], ...]:
        task_by_milestone: dict[str, list[Mapping[str, object]]] = {}
        parent_by_milestone: dict[str, Mapping[str, object]] = {}
        for task in tasks:
            inputs = task.get("inputs") if isinstance(task.get("inputs"), Mapping) else {}
            milestone_id = str(inputs.get("milestone_id") or "")
            if not milestone_id:
                continue
            task_by_milestone.setdefault(milestone_id, []).append(task)
            if inputs.get("kind") == "milestone":
                parent_by_milestone[milestone_id] = task
        result: list[dict[str, object]] = []
        for milestone in persisted_milestones(project_id, database_path=self.database_path):
            milestone_id = str(milestone["milestone_id"])
            child_ids = [
                str(item.get("task_id"))
                for item in milestone.get("deliverables", ())
                if isinstance(item, Mapping) and item.get("task_id")
            ]
            child_tasks = [task for task in task_by_milestone.get(milestone_id, ()) if task.get("id") in child_ids]
            states = {str(task["state"]) for task in child_tasks}
            if child_tasks and states <= {TaskState.COMPLETED.value}:
                computed = "completed"
            elif states & {TaskState.BLOCKED.value, TaskState.FAILED.value}:
                computed = "blocked"
            elif states & {TaskState.ASSIGNED.value, TaskState.RUNNING.value, TaskState.REVIEW.value}:
                computed = "active"
            else:
                computed = str(milestone.get("state") or "planned")
            result.append(
                {
                    **dict(milestone),
                    "task_id": parent_by_milestone.get(milestone_id, {}).get("id"),
                    "task_ids": child_ids,
                    "computed_state": computed,
                }
            )
        return tuple(result)

    def status_report(self, project_id: str) -> ProjectStatusReport:
        project = self._project(project_id)
        tasks = coordination_store.list_tasks(project_id=project_id, limit=500, database_path=self.database_path)
        blocked = self.detect_blocked_tasks(project_id)
        tasks = coordination_store.list_tasks(project_id=project_id, limit=500, database_path=self.database_path)
        counts: dict[str, int] = {}
        for task in tasks:
            state = str(task["state"])
            counts[state] = counts.get(state, 0) + 1
        completed = tuple(
            {"task_id": task["id"], "title": task["title"], "role": task["role"]}
            for task in tasks if task["state"] == TaskState.COMPLETED.value
        )
        current = tuple(
            {"task_id": task["id"], "title": task["title"], "role": task["role"], "state": task["state"]}
            for task in tasks if task["state"] in {TaskState.ASSIGNED.value, TaskState.RUNNING.value, TaskState.REVIEW.value}
        )
        pending = tuple(
            {"task_id": task["id"], "title": task["title"], "role": task["role"], "state": task["state"]}
            for task in tasks if task["state"] in {TaskState.PENDING.value, TaskState.READY.value}
        )
        dependencies = tuple(
            {"task_id": item["id"], "depends_on_task_id": dependency}
            for item in tasks for dependency in item.get("dependencies", ())
        )
        risks = tuple(list_risks(project_id, status="open", database_path=self.database_path))
        open_requests = tuple(list_work_requests(project_id=project_id, status="open", database_path=self.database_path))
        messages = self.bus.relevant(project_id=project_id, topic="scope_escalation", limit=100)
        scope_escalations = tuple(
            {
                "message_id": item["message_id"],
                "subject": item["subject"],
                "body": item["body"],
                "created_at": item["created_at"],
            }
            for item in messages if item.get("message_type") == MessageType.BLOCKER.value
        )
        next_actions: list[str] = []
        if blocked:
            next_actions.append("Resolve blocked dependencies or reassign blocked tasks.")
        if pending:
            next_actions.append("Schedule ready deliverables through the existing work queue.")
        if not pending and not current and not blocked and tasks:
            next_actions.append("Review completion evidence and report delivery status.")
        if risks:
            next_actions.append("Review open project risks and confirm mitigation owners.")
        return ProjectStatusReport(
            project_id=project_id,
            project=project,
            task_counts=counts,
            completed_work=completed,
            current_work=current,
            pending_work=pending,
            blocked_tasks=tuple(blocked),
            dependencies=dependencies,
            milestones=self._milestone_status(project_id, tasks),
            risks=risks,
            open_requests=open_requests,
            scope_escalations=scope_escalations,
            next_actions=tuple(next_actions),
        )

    def list_milestones(self, project_id: str) -> tuple[dict[str, object], ...]:
        self._project(project_id)
        tasks = coordination_store.list_tasks(project_id=project_id, limit=500, database_path=self.database_path)
        return self._milestone_status(project_id, tasks)

    project_status_report = status_report
    blocked_tasks = detect_blocked_tasks
    status = status_report
    report = status_report

    def request_status_update(
        self,
        project_id: str,
        *,
        recipient_roles: Iterable[str] = (),
        task_ids: Iterable[str] = (),
        run_id: str | None = None,
        reason: str = "scheduled project status update",
    ) -> list[dict[str, object]]:
        self.ensure_profile()
        self._project(project_id)
        recipients = list(_items(recipient_roles, max_chars=128))
        if not recipients:
            tasks = coordination_store.list_tasks(project_id=project_id, limit=500, database_path=self.database_path)
            recipients = list(dict.fromkeys(str(task["role"]) for task in tasks if task["state"] in {"assigned", "running", "blocked", "review"}))
        if not recipients:
            recipients = ["engineering_manager"]
        body = json.dumps({"project_id": project_id, "reason": _clean(reason), "requested_by": self.ROLE}, ensure_ascii=False)
        requested_task_ids = tuple(_items(task_ids, max_chars=128))
        return [
            self.bus.publish(
                sender_role=self.ROLE,
                recipient_role=recipient,
                message_type=MessageType.STATUS,
                subject="Project Manager status request",
                body=body,
                project_id=project_id,
                run_id=run_id,
                task_id=str(task_id) if task_id else None,
                topic="status_request",
            )
            for recipient in recipients
            for task_id in (requested_task_ids or (None,))
        ]

    def escalate_scope(
        self,
        project_id: str,
        *,
        reason: str,
        requested_change: str,
        affected_task_ids: Iterable[str] = (),
        target_role: str = "company_director",
        run_id: str | None = None,
    ) -> dict[str, object]:
        self.ensure_profile()
        self._project(project_id)
        if target_role not in {"company_director", "supervisor"}:
            raise ValueError("scope escalations must target Company Director or Supervisor")
        affected = self._validate_task_ids(project_id, affected_task_ids)
        escalation = ScopeEscalation(
            escalation_id=str(uuid4()),
            project_id=project_id,
            reason=_clean(reason, max_chars=4000),
            requested_change=_clean(requested_change, max_chars=4000),
            affected_task_ids=affected,
            target_role=target_role,
        )
        message = self.bus.publish(
            sender_role=self.ROLE,
            recipient_role=target_role,
            message_type=MessageType.BLOCKER,
            subject="Project scope escalation requires owner decision",
            body=json.dumps(escalation.as_dict(), ensure_ascii=False),
            run_id=run_id,
            project_id=project_id,
            references=affected,
            topic="scope_escalation",
        )
        return {**escalation.as_dict(), "message_id": message["message_id"], "message": message}

    def escalate_delay(self, project_id: str, *, reason: str, affected_task_ids: Iterable[str] = (), run_id: str | None = None) -> dict[str, object]:
        return self.escalate_scope(
            project_id,
            reason=reason,
            requested_change="Re-plan delivery dates and dependencies after the reported delay.",
            affected_task_ids=affected_task_ids,
            run_id=run_id,
        )

    def add_risk(self, project_id: str, title: str, *, severity: str = "medium", mitigation: str = "", owner: str | None = None) -> dict[str, object]:
        self.ensure_profile()
        self._project(project_id)
        return persist_risk(project_id, _clean(title, max_chars=500), severity=severity, mitigation=_clean(mitigation, max_chars=10_000), owner=owner, database_path=self.database_path)

    def handoff(self, project_id: str, *, target_role: str, summary: str, task_id: str | None = None, run_id: str | None = None, completed: Iterable[str] = (), remaining_work: Iterable[str] = (), risks: Iterable[str] = ()) -> dict[str, object]:
        self.ensure_profile()
        self._project(project_id)
        if target_role not in self._HANDOFF_TARGETS:
            raise ValueError(f"Project Manager cannot handoff to {target_role}")
        handoff = coordination_store.create_handoff(
            AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target_role,
                summary=_clean(summary, max_chars=20_000),
                completed=_items(completed),
                risks=_items(risks),
                remaining_work=_items(remaining_work),
                verification=("No workspace files changed by Project Manager.",),
                run_id=run_id,
                project_id=project_id,
                task_id=task_id,
                status="submitted",
            ),
            database_path=self.database_path,
        )
        message = self.bus.publish(
            sender_role=self.ROLE,
            recipient_role=target_role,
            message_type=MessageType.HANDOFF,
            subject="Project Manager delivery handoff",
            body=json.dumps(handoff, ensure_ascii=False),
            run_id=run_id,
            project_id=project_id,
            task_id=task_id,
            references=(str(handoff["handoff_id"]),),
            topic="delivery_handoff",
        )
        return {"handoff": handoff, "message": message}


ProjectManager = ProjectManagerAgent


__all__ = [
    "DeliverablePlan",
    "MilestonePlan",
    "ProjectManager",
    "ProjectManagerAgent",
    "ProjectStatusReport",
    "ScopeEscalation",
]
