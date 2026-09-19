from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, CoordinationTask, MessageType, TaskState
from app.coordination.project_management import enqueue_work
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_HANDOFF_TARGETS = frozenset({"integration", "tester"})
_RELATIVE_RESOURCE = re.compile(r"^[A-Za-z]:")


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _items(values: Iterable[object] | None, *, limit: int = 100, max_chars: int = 2000) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for value in values or ():
        item = _clean(value, max_chars=max_chars)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)


def _mapping_items(values: Iterable[object] | None, *, limit: int = 100) -> tuple[dict[str, object], ...]:
    result: list[dict[str, object]] = []
    for value in values or ():
        if hasattr(value, "as_dict") and callable(value.as_dict):
            value = value.as_dict()
        if isinstance(value, Mapping):
            item: dict[str, object] = {}
            for key, raw in value.items():
                clean_key = _clean(key, max_chars=128)
                if not clean_key:
                    continue
                if isinstance(raw, Mapping):
                    item[clean_key] = {
                        str(k): (dict(v) if isinstance(v, Mapping) else _clean(v, max_chars=2000))
                        for k, v in raw.items()
                    }
                elif isinstance(raw, (list, tuple, set)):
                    item[clean_key] = [
                        dict(entry) if isinstance(entry, Mapping) else _clean(entry, max_chars=2000)
                        for entry in raw
                    ]
                else:
                    item[clean_key] = _clean(raw, max_chars=4000)
            if item and item not in result:
                result.append(item)
        else:
            text = _clean(value, max_chars=2000)
            if text:
                result.append({"description": text})
        if len(result) >= limit:
            break
    return tuple(result)


def _resources(values: Iterable[object] | None, *, limit: int = 100) -> tuple[str, ...]:
    resources: list[str] = []
    for raw in values or ():
        item = _clean(raw, max_chars=512).replace("\\", "/").strip("/")
        if not item or item in resources:
            continue
        parts = item.split("/")
        if _RELATIVE_RESOURCE.match(item) or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("backend resource scope must be project-relative")
        resources.append(item)
        if len(resources) >= limit:
            break
    return tuple(resources)


def _handoff_target(value: object) -> str:
    target = _clean(value, max_chars=128).casefold()
    if target not in _HANDOFF_TARGETS:
        raise ValueError("backend handoffs must target integration or tester")
    return target


@dataclass(frozen=True)
class BackendImplementationPlan:
    plan_id: str
    task_id: str
    project_id: str
    requirements: tuple[str, ...] = ()
    architecture_refs: tuple[str, ...] = ()
    api_contracts: tuple[dict[str, object], ...] = ()
    security_requirements: tuple[str, ...] = ()
    migration_plan: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    test_plan: tuple[str, ...] = ()
    inspection_evidence: tuple[str, ...] = ()
    handoff_targets: tuple[str, ...] = ("integration", "tester")
    status: str = "planned"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in (
            "requirements",
            "architecture_refs",
            "security_requirements",
            "migration_plan",
            "scope",
            "acceptance_criteria",
            "test_plan",
            "inspection_evidence",
            "handoff_targets",
        ):
            result[key] = list(getattr(self, key))
        result["api_contracts"] = list(self.api_contracts)
        return result


@dataclass(frozen=True)
class BackendClaim:
    task_id: str
    project_id: str
    agent_id: str
    resources: tuple[str, ...]
    previous_state: str
    state: str
    lock_acquired: bool
    blocked_by: tuple[str, ...] = ()
    message_id: str | None = None
    status: str = "claimed"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["resources"] = list(self.resources)
        result["blocked_by"] = list(self.blocked_by)
        return result


@dataclass(frozen=True)
class BackendImplementationResult:
    task_id: str
    project_id: str
    status: str
    code_changes: tuple[str, ...] = ()
    migration_changes: tuple[str, ...] = ()
    files_changed: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    technical_notes: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    handoff_ids: tuple[str, ...] = ()
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in (
            "code_changes",
            "migration_changes",
            "files_changed",
            "tests",
            "technical_notes",
            "verification",
            "handoff_ids",
        ):
            result[key] = list(getattr(self, key))
        return result


class BackendEngineerAgent:
    """Scoped backend implementer using the existing task, lock and Local Agent boundaries."""

    ROLE = "backend"
    DISPLAY_NAME = "Backend Engineer"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-backend",
            display_name=self.DISPLAY_NAME,
            department=Department.ENGINEERING,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Backend task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Backend Engineer can only operate backend tasks")
        return task

    def _publish(
        self,
        *,
        message_type: MessageType,
        subject: str,
        body: str,
        project_id: str,
        task_id: str | None = None,
        run_id: str | None = None,
        recipient_role: str | None = None,
        references: Iterable[str] = (),
        topic: str = "backend_engineering",
    ) -> dict[str, object]:
        return self.bus.publish(
            sender_role=self.ROLE,
            message_type=message_type,
            subject=_clean(subject, max_chars=500),
            body=_clean(body, max_chars=20_000),
            project_id=project_id,
            task_id=task_id,
            run_id=run_id,
            recipient_role=recipient_role,
            references=_items(references, max_chars=512),
            topic=topic,
        )

    def prepare(
        self,
        task_id: str,
        *,
        requirements: Iterable[object] = (),
        architecture_refs: Iterable[object] = (),
        api_contracts: Iterable[object] = (),
        security_requirements: Iterable[object] = (),
        migration_plan: Iterable[object] = (),
        scope: Iterable[object] | None = None,
        acceptance_criteria: Iterable[object] = (),
        test_plan: Iterable[object] = (),
        inspection_evidence: Iterable[object] = (),
        handoff_targets: Iterable[object] = ("integration", "tester"),
        run_id: str | None = None,
    ) -> BackendImplementationPlan:
        """Create a bounded implementation plan after relevant inspection evidence exists."""
        task = self._task(task_id)
        evidence = _items(inspection_evidence, max_chars=500)
        if not evidence:
            raise ValueError("relevant existing-code inspection evidence is required before backend work")
        resources = _resources(scope if scope is not None else task.get("scope") or ())
        if not resources:
            raise ValueError("backend implementation requires a non-empty scoped workspace")
        targets = tuple(dict.fromkeys(_handoff_target(item) for item in handoff_targets))
        if not targets:
            raise ValueError("backend implementation requires an integration or tester handoff")
        plan = BackendImplementationPlan(
            plan_id=str(uuid4()),
            task_id=str(task["id"]),
            project_id=str(task["project_id"]),
            requirements=_items(requirements),
            architecture_refs=_items(architecture_refs, max_chars=500),
            api_contracts=_mapping_items(api_contracts),
            security_requirements=_items(security_requirements),
            migration_plan=_items(migration_plan),
            scope=resources,
            acceptance_criteria=_items(acceptance_criteria),
            test_plan=_items(test_plan),
            inspection_evidence=evidence,
            handoff_targets=targets,
        )
        message = self._publish(
            message_type=MessageType.STATUS,
            subject=f"Backend plan: {task.get('title', task_id)}",
            body=json.dumps(plan.as_dict(), ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=evidence + tuple(f"architecture:{item}" for item in plan.architecture_refs),
            topic="backend_plan",
        )
        return BackendImplementationPlan(**{**asdict(plan), "message_id": str(message["message_id"])})

    def _dependencies_ready(self, task_id: str) -> tuple[bool, tuple[str, ...]]:
        blocked: list[str] = []
        for dependency in coordination_store.list_dependencies(task_id, database_path=self.database_path):
            dependency_id = str(dependency.get("depends_on_task_id") or "")
            dependency_task = coordination_store.get_task(dependency_id, database_path=self.database_path)
            if not dependency_task or dependency_task.get("state") != TaskState.COMPLETED.value:
                blocked.append(dependency_id or "missing_dependency")
        return not blocked, tuple(blocked)

    def claim(
        self,
        task_id: str,
        *,
        resources: Iterable[object] | None = None,
        agent_id: str = "employee-backend",
        lease_seconds: int = 1800,
        run_id: str | None = None,
    ) -> BackendClaim:
        """Claim a backend task only after dependencies and workspace locks are safe."""
        self.ensure_profile()
        task = self._task(task_id)
        task_resources = _resources(resources if resources is not None else task.get("scope") or ())
        if not task_resources:
            raise ValueError("backend task claim requires a non-empty workspace scope")
        previous = str(task.get("state") or TaskState.PENDING.value)
        ready, blocked = self._dependencies_ready(str(task["id"]))
        if not ready:
            if previous in {TaskState.PENDING.value, TaskState.READY.value}:
                task = coordination_store.transition(str(task["id"]), TaskState.BLOCKED, failure_reason="Incomplete backend dependencies: " + ", ".join(blocked), database_path=self.database_path)
            message = self._publish(
                message_type=MessageType.BLOCKER,
                subject=f"Backend task blocked: {task.get('title', task_id)}",
                body="Incomplete dependencies: " + ", ".join(blocked),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                recipient_role="engineering_manager",
                references=tuple(f"task:{item}" for item in blocked),
                topic="backend_blocker",
            )
            return BackendClaim(str(task["id"]), str(task["project_id"]), agent_id, task_resources, previous, str(task["state"]), False, blocked, str(message["message_id"]), "blocked")
        acquired: list[str] = []
        for resource in task_resources:
            if not coordination_store.acquire_lock(resource, str(task["id"]), self.ROLE, lease_seconds=lease_seconds, database_path=self.database_path):
                for locked in acquired:
                    coordination_store.release_lock(locked, str(task["id"]), database_path=self.database_path)
                if previous in {TaskState.PENDING.value, TaskState.READY.value}:
                    task = coordination_store.transition(str(task["id"]), TaskState.BLOCKED, failure_reason=f"Workspace resource is locked: {resource}", database_path=self.database_path)
                message = self._publish(
                    message_type=MessageType.BLOCKER,
                    subject=f"Backend workspace conflict: {task.get('title', task_id)}",
                    body=f"Workspace resource is locked: {resource}",
                    project_id=str(task["project_id"]),
                    task_id=str(task["id"]),
                    run_id=run_id or task.get("run_id"),
                    recipient_role="engineering_manager",
                    references=(f"resource:{resource}",),
                    topic="backend_blocker",
                )
                return BackendClaim(str(task["id"]), str(task["project_id"]), agent_id, task_resources, previous, str(task["state"]), False, (resource,), str(message["message_id"]), "blocked")
            acquired.append(resource)
        current = str(task.get("state") or previous)
        if current in {TaskState.PENDING.value, TaskState.BLOCKED.value, TaskState.FAILED.value}:
            task = coordination_store.transition(str(task["id"]), TaskState.READY, failure_reason=None, database_path=self.database_path)
            current = str(task["state"])
        if current == TaskState.READY.value:
            task = coordination_store.transition(str(task["id"]), TaskState.ASSIGNED, assigned_agent=agent_id, database_path=self.database_path)
            current = str(task["state"])
        elif current == TaskState.ASSIGNED.value and str(task.get("assigned_agent") or "") not in {agent_id, self.ROLE}:
            for locked in acquired:
                coordination_store.release_lock(locked, str(task["id"]), database_path=self.database_path)
            raise ValueError("backend task is already assigned to another agent")
        if current == TaskState.ASSIGNED.value:
            task = coordination_store.transition(str(task["id"]), TaskState.RUNNING, assigned_agent=agent_id, database_path=self.database_path)
            current = str(task["state"])
        elif current != TaskState.RUNNING.value:
            for locked in acquired:
                coordination_store.release_lock(locked, str(task["id"]), database_path=self.database_path)
            raise ValueError(f"backend task is not claimable from state: {current}")
        message = self._publish(
            message_type=MessageType.STATUS,
            subject=f"Backend task claimed: {task.get('title', task_id)}",
            body=json.dumps({"agent_id": agent_id, "resources": list(task_resources), "state": current}, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=tuple(f"resource:{item}" for item in task_resources),
            topic="backend_execution",
        )
        return BackendClaim(str(task["id"]), str(task["project_id"]), agent_id, task_resources, previous, current, True, (), str(message["message_id"]), "claimed")

    def release_locks(self, task_id: str, resources: Iterable[object]) -> int:
        released = 0
        for resource in _resources(resources):
            if coordination_store.release_lock(resource, str(task_id), database_path=self.database_path):
                released += 1
        return released

    def record_result(
        self,
        task_id: str,
        *,
        code_changes: Iterable[object] = (),
        migration_changes: Iterable[object] = (),
        files_changed: Iterable[object] = (),
        tests: Iterable[object] = (),
        technical_notes: Iterable[object] = (),
        verification: Iterable[object] = (),
        handoff_targets: Iterable[object] = ("integration", "tester"),
        run_id: str | None = None,
    ) -> BackendImplementationResult:
        """Record evidence and hand work to Integration/QA; never self-approves completion."""
        task = self._task(task_id)
        state = str(task.get("state") or "")
        if state == TaskState.ASSIGNED.value:
            task = coordination_store.transition(str(task["id"]), TaskState.RUNNING, database_path=self.database_path)
            state = TaskState.RUNNING.value
        if state != TaskState.RUNNING.value:
            raise ValueError(f"backend result requires a running task, not {state}")
        code = _items(code_changes, max_chars=4000)
        migrations = _items(migration_changes, max_chars=4000)
        tests_run = _items(tests, max_chars=1000)
        verification_items = _items(verification, max_chars=500)
        if not code and not migrations:
            raise ValueError("backend result must include code or migration changes")
        if not tests_run and not verification_items:
            raise ValueError("backend result requires test or verification evidence")
        targets = tuple(dict.fromkeys(_handoff_target(item) for item in handoff_targets))
        changed = _resources(files_changed)
        notes = _items(technical_notes)
        payload = {
            "task_id": str(task["id"]),
            "project_id": str(task["project_id"]),
            "code_changes": list(code),
            "migration_changes": list(migrations),
            "files_changed": list(changed),
            "tests": list(tests_run),
            "technical_notes": list(notes),
            "verification": list(verification_items),
            "handoff_targets": list(targets),
        }
        result_message = self._publish(
            message_type=MessageType.RESULT,
            subject=f"Backend implementation result: {task.get('title', task_id)}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=tuple(f"file:{item}" for item in changed),
            topic="backend_result",
        )
        task = coordination_store.transition(str(task["id"]), TaskState.REVIEW, database_path=self.database_path)
        handoff_ids: list[str] = []
        for target in targets:
            handoff = AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target,
                summary=f"Backend implementation: {task.get('title', task_id)}",
                completed=("Backend code and service logic implemented.", "Validation evidence recorded.", "Workspace scope released after implementation."),
                artifacts=("code_changes", "migration_changes", "tests", "technical_notes"),
                changed_files=changed,
                decisions=tests_run,
                risks=notes,
                remaining_work=("Run independent integration and QA verification.",),
                verification=verification_items,
                run_id=run_id or task.get("run_id"),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
            )
            row = self.handoffs.submit(handoff)
            handoff_ids.append(str(row["handoff_id"]))
            self._publish(
                message_type=MessageType.HANDOFF,
                subject=handoff.summary,
                body=json.dumps({"handoff": row, "result": payload}, ensure_ascii=False),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                recipient_role=target,
                references=(f"handoff:{row['handoff_id']}", f"task:{task['id']}"),
                topic="backend_handoff",
            )
            enqueue_work(target, str(task["project_id"]), "handoff", str(row["handoff_id"]), task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        self.release_locks(str(task["id"]), task.get("scope") or changed)
        return BackendImplementationResult(str(task["id"]), str(task["project_id"]), TaskState.REVIEW.value, code, migrations, changed, tests_run, notes, verification_items, tuple(handoff_ids), str(result_message["message_id"]))

    def complete(self, *args: object, **kwargs: object) -> BackendImplementationResult:
        return self.record_result(*args, **kwargs)


BackendEngineer = BackendEngineerAgent


__all__ = [
    "BackendClaim",
    "BackendEngineer",
    "BackendEngineerAgent",
    "BackendImplementationPlan",
    "BackendImplementationResult",
]
