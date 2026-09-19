from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.collaboration_store import create_decision, list_decisions
from app.coordination.models import MessageType, TaskState, TechnicalDecision
from app.coordination.bus import MessageBus
from app.coordination.project_management import enqueue_work, list_quality_gates
from app.coordination.roles import ROLE_ALIASES, ROLE_REGISTRY, resolve_role
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_TECHNICAL_ROLES = frozenset({
    "architect", "backend", "frontend", "implementer", "integration",
    "tester", "debugger", "reviewer", "security", "docs",
    "release_verifier", "researcher",
})
_ACTIVE_STATES = frozenset({
    TaskState.PENDING.value, TaskState.READY.value, TaskState.ASSIGNED.value,
    TaskState.RUNNING.value, TaskState.WAITING.value, TaskState.BLOCKED.value,
    TaskState.REVIEW.value, TaskState.FAILED.value,
})


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


def _role(value: object) -> str:
    normalized = _clean(value, max_chars=128).casefold()
    if normalized not in ROLE_REGISTRY and normalized not in ROLE_ALIASES:
        raise ValueError(f"unknown agent role: {value}")
    resolved = resolve_role(normalized)
    if resolved not in _TECHNICAL_ROLES:
        raise ValueError(f"Engineering Manager cannot delegate to non-technical role: {value}")
    return resolved


@dataclass(frozen=True)
class TechnicalDelegation:
    task_id: str
    project_id: str
    assigned_role: str
    assigned_agent: str
    previous_state: str
    state: str
    rationale: str
    evidence: tuple[str, ...] = ()
    queue_id: str | None = None
    message_id: str | None = None
    status: str = "assigned"

    @property
    def target_role(self) -> str:
        return self.assigned_role

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["target_role"] = self.assigned_role
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class TechnicalConflictResolution:
    conflict_id: str
    project_id: str
    subject: str
    decision: str
    decision_id: str
    message_id: str
    evidence: tuple[str, ...] = ()
    affected_task_ids: tuple[str, ...] = ()
    status: str = "resolved"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        result["affected_task_ids"] = list(self.affected_task_ids)
        return result


@dataclass(frozen=True)
class BlockerReport:
    task_id: str
    project_id: str
    reason: str
    state: str
    escalated_to: str
    message_id: str
    reassignment: TechnicalDelegation | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["reassignment"] = self.reassignment.as_dict() if self.reassignment else None
        return result


@dataclass(frozen=True)
class TechnicalReadiness:
    project_id: str
    ready: bool
    task_counts: Mapping[str, int]
    evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    failed_tests: tuple[str, ...] = ()
    open_reviews: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["task_counts"] = dict(self.task_counts)
        for key in ("evidence", "missing_evidence", "failed_tests", "open_reviews", "blockers"):
            result[key] = list(getattr(self, key))
        return result


class EngineeringManagerAgent:
    """Technical execution manager using the existing DAG, bus and queues.

    The profile is read-only: this role coordinates specialist writers and
    cannot replace them with direct workspace edits.
    """

    ROLE = "engineering_manager"
    DISPLAY_NAME = "Engineering Manager"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-engineering-manager",
            display_name=self.DISPLAY_NAME,
            department=Department.ENGINEERING,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _get_task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Task not found: {task_id}")
        return task

    def _task_in_project(self, task_id: str, project_id: str) -> dict[str, object]:
        task = self._get_task(task_id)
        if str(task["project_id"]) != str(project_id):
            raise ValueError("Engineering Manager cannot mix tasks across projects")
        return task

    def _validate_tasks(self, project_id: str, task_ids: Iterable[object]) -> tuple[str, ...]:
        result: list[str] = []
        for raw in task_ids:
            task_id = _clean(raw, max_chars=128)
            if not task_id or task_id in result:
                continue
            self._task_in_project(task_id, project_id)
            result.append(task_id)
        return tuple(result)

    def _dependencies_ready(self, task_id: str) -> tuple[bool, tuple[str, ...]]:
        blocked: list[str] = []
        for dependency in coordination_store.list_dependencies(task_id, database_path=self.database_path):
            dependency_id = str(dependency.get("depends_on_task_id") or "")
            dependency_task = coordination_store.get_task(dependency_id, database_path=self.database_path)
            if not dependency_task or dependency_task.get("state") != TaskState.COMPLETED.value:
                blocked.append(dependency_id or "missing_dependency")
        return not blocked, tuple(blocked)

    def _publish(self, *, message_type: MessageType, subject: str, body: str,
                 project_id: str, task_id: str | None = None, run_id: str | None = None,
                 recipient_role: str | None = None, references: Iterable[str] = (),
                 topic: str = "engineering_management") -> dict[str, object]:
        return self.bus.publish(
            sender_role=self.ROLE, message_type=message_type,
            subject=_clean(subject, max_chars=500), body=_clean(body, max_chars=20_000),
            project_id=project_id, task_id=task_id, run_id=run_id,
            recipient_role=recipient_role, references=_items(references, max_chars=128), topic=topic,
        )

    def analyze_workload(self, project_id: str, *, limit: int = 500) -> dict[str, object]:
        tasks = coordination_store.list_tasks(project_id=project_id, limit=min(max(int(limit), 1), 500), database_path=self.database_path)
        by_role: dict[str, int] = {}
        by_state: dict[str, int] = {}
        unassigned: list[dict[str, object]] = []
        blocked: list[dict[str, object]] = []
        reviews: list[dict[str, object]] = []
        active: list[dict[str, object]] = []
        for task in tasks:
            role = str(task.get("role") or "unassigned")
            state = str(task.get("state") or TaskState.PENDING.value)
            by_role[role] = by_role.get(role, 0) + 1
            by_state[state] = by_state.get(state, 0) + 1
            if not task.get("assigned_agent") and state in _ACTIVE_STATES:
                unassigned.append(task)
            if state == TaskState.BLOCKED.value:
                blocked.append(task)
            if state == TaskState.REVIEW.value:
                reviews.append(task)
            if state in {TaskState.ASSIGNED.value, TaskState.RUNNING.value, TaskState.WAITING.value}:
                active.append(task)
        return {"project_id": project_id, "total_tasks": len(tasks), "by_role": by_role,
                "by_state": by_state, "unassigned": unassigned, "blocked": blocked,
                "open_reviews": reviews, "active": active}

    def select_role(self, task: Mapping[str, object], *, preferred_role: str | None = None) -> str:
        if preferred_role:
            return _role(preferred_role)
        declared = str(task.get("role") or "").strip()
        if declared:
            try:
                return _role(declared)
            except ValueError:
                pass
        text = f"{task.get('title', '')} {task.get('description', '')}".casefold()
        for words, role in ((
            (("security", "threat", "auth"), "security"),
            (("test", "qa", "verify"), "tester"),
            (("review", "quality"), "reviewer"),
            (("frontend", "ui", "client"), "frontend"),
            (("backend", "api", "server"), "backend"),
            (("integration", "contract", "merge"), "integration"),
            (("architecture", "design"), "architect"),
        )):
            if any(word in text for word in words):
                return role
        return "implementer"

    def _blocked_result(self, task: Mapping[str, object], *, assigned_role: str,
                        assigned_agent: str, previous_state: str, rationale: str,
                        evidence: tuple[str, ...], reason: str, run_id: str | None) -> TechnicalDelegation:
        task_id, project_id = str(task["id"]), str(task["project_id"])
        current = previous_state
        if current in {TaskState.PENDING.value, TaskState.READY.value}:
            try:
                task = coordination_store.transition(task_id, TaskState.BLOCKED, failure_reason=reason, database_path=self.database_path)
                current = str(task["state"])
            except ValueError:
                pass
        message = self._publish(message_type=MessageType.BLOCKER,
            subject=f"Task blocked: {task.get('title', task_id)}", body=reason,
            project_id=project_id, task_id=task_id, run_id=run_id,
            recipient_role="supervisor", references=evidence, topic="engineering_blocker")
        return TechnicalDelegation(task_id=task_id, project_id=project_id, assigned_role=assigned_role,
            assigned_agent=assigned_agent, previous_state=previous_state, state=current,
            rationale=rationale, evidence=evidence, message_id=str(message["message_id"]), status="blocked")

    def delegate_task(self, task_id: str, target_role: str | None = None, *, target_agent: str | None = None,
                      rationale: str = "", evidence: Iterable[object] = (), run_id: str | None = None,
                      priority: int | None = None) -> TechnicalDelegation:
        self.ensure_profile()
        task = self._get_task(task_id)
        role = self.select_role(task, preferred_role=target_role)
        agent = _clean(target_agent or role, max_chars=128) or role
        rationale = _clean(rationale, max_chars=4000) or "Technical workload assignment"
        evidence = _items(evidence)
        previous = str(task.get("state") or TaskState.PENDING.value)
        ready, dependencies = self._dependencies_ready(task_id)
        if not ready:
            return self._blocked_result(task, assigned_role=role, assigned_agent=agent,
                previous_state=previous, rationale=rationale, evidence=evidence + dependencies,
                reason="Task is waiting for incomplete dependencies: " + ", ".join(dependencies),
                run_id=run_id or task.get("run_id"))
        if previous in {TaskState.PENDING.value, TaskState.BLOCKED.value, TaskState.FAILED.value, TaskState.WAITING.value}:
            try:
                task = coordination_store.transition(task_id, TaskState.READY, failure_reason=None, database_path=self.database_path)
            except ValueError:
                task = self._get_task(task_id)
        current = str(task.get("state") or previous)
        if current == TaskState.READY.value:
            task = coordination_store.transition(task_id, TaskState.ASSIGNED, assigned_agent=agent, database_path=self.database_path)
        elif current == TaskState.ASSIGNED.value:
            if str(task.get("assigned_agent") or "") not in {agent, role}:
                raise ValueError("task is already assigned; use reassign_task")
        elif current in {TaskState.COMPLETED.value, TaskState.CANCELLED.value, TaskState.REVIEW.value}:
            raise ValueError(f"cannot delegate task in terminal/review state: {current}")
        else:
            raise ValueError(f"task is not delegable from state: {current}")
        queue = enqueue_work(agent, str(task["project_id"]), "task", str(task["id"]), task_id=str(task["id"]),
            priority=int(priority if priority is not None else task.get("priority") or 50), database_path=self.database_path)
        message = self._publish(message_type=MessageType.HANDOFF,
            subject=f"Technical task delegated: {task.get('title', task_id)}", body=rationale,
            project_id=str(task["project_id"]), task_id=str(task["id"]), run_id=run_id or task.get("run_id"),
            recipient_role=role, references=evidence + (f"task:{task_id}",))
        return TechnicalDelegation(task_id=str(task["id"]), project_id=str(task["project_id"]), assigned_role=role,
            assigned_agent=agent, previous_state=previous, state=TaskState.ASSIGNED.value, rationale=rationale,
            evidence=evidence, queue_id=str(queue["queue_id"]), message_id=str(message["message_id"]))

    def reassign_task(self, task_id: str, new_role: str, *, new_agent: str | None = None,
                      reason: str = "", evidence: Iterable[object] = (), run_id: str | None = None) -> TechnicalDelegation:
        task = self._get_task(task_id)
        state = str(task.get("state") or "")
        if state in {TaskState.COMPLETED.value, TaskState.CANCELLED.value}:
            raise ValueError("completed or cancelled tasks cannot be reassigned")
        if state in {TaskState.ASSIGNED.value, TaskState.RUNNING.value, TaskState.REVIEW.value}:
            coordination_store.transition(task_id, TaskState.WAITING,
                failure_reason=_clean(reason, max_chars=4000) or "Engineering Manager reassignment",
                database_path=self.database_path)
        return self.delegate_task(task_id, new_role, target_agent=new_agent,
            rationale=_clean(reason, max_chars=4000) or "Reassigned by Engineering Manager",
            evidence=evidence, run_id=run_id)

    def request_review(self, task_id: str, *, reviewer_role: str = "reviewer",
                       evidence: Iterable[object] = (), run_id: str | None = None) -> dict[str, object]:
        task = self._get_task(task_id)
        role = _role(reviewer_role)
        if role not in {"reviewer", "security", "release_verifier"}:
            raise ValueError("reviewer_role must be a review-capable role")
        state = str(task.get("state") or "")
        if state == TaskState.ASSIGNED.value:
            coordination_store.transition(task_id, TaskState.RUNNING, database_path=self.database_path)
            state = TaskState.RUNNING.value
        if state == TaskState.RUNNING.value:
            coordination_store.transition(task_id, TaskState.REVIEW, database_path=self.database_path)
        elif state != TaskState.REVIEW.value:
            raise ValueError(f"cannot request review from task state: {state}")
        queue = enqueue_work(role, str(task["project_id"]), "review", str(task["id"]), task_id=str(task["id"]),
            priority=int(task.get("priority") or 50), database_path=self.database_path)
        message = self._publish(message_type=MessageType.REVIEW,
            subject=f"Review requested: {task.get('title', task_id)}",
            body="Independent review requested before technical readiness.", project_id=str(task["project_id"]),
            task_id=str(task["id"]), run_id=run_id or task.get("run_id"), recipient_role=role,
            references=_items(evidence) + (f"task:{task_id}",), topic="review_request")
        return {"task_id": str(task["id"]), "project_id": str(task["project_id"]), "reviewer_role": role,
                "queue_id": queue["queue_id"], "message_id": message["message_id"], "state": TaskState.REVIEW.value}

    def resolve_technical_conflict(self, project_id: str, subject: str, decision: str, *, context: str = "",
                                   options: Iterable[object] = (), arguments: Iterable[object] = (),
                                   evidence: Iterable[object] = (), affected_task_ids: Iterable[object] = (),
                                   run_id: str | None = None, notify_role: str = "supervisor") -> TechnicalConflictResolution:
        self.ensure_profile()
        title, outcome = _clean(subject, max_chars=500), _clean(decision, max_chars=20_000)
        if not title or not outcome:
            raise ValueError("technical conflict subject and decision are required")
        tasks, evidence = self._validate_tasks(project_id, affected_task_ids), _items(evidence)
        record = create_decision(TechnicalDecision(project_id=project_id, run_id=run_id, title=title,
            context=_clean(context, max_chars=20_000), options=_items(options), arguments=_items(arguments),
            decision=outcome, decision_maker=self.ROLE, supporting_evidence=evidence, affected_tasks=tasks),
            database_path=self.database_path)
        message = self._publish(message_type=MessageType.DECISION, subject=title, body=outcome,
            project_id=project_id, run_id=run_id, recipient_role=notify_role,
            references=evidence + (f"decision:{record['decision_id']}",), topic="technical_decision")
        return TechnicalConflictResolution(conflict_id=str(uuid4()), project_id=project_id, subject=title,
            decision=outcome, decision_id=str(record["decision_id"]), message_id=str(message["message_id"]),
            evidence=evidence, affected_task_ids=tasks)

    def handle_blocked_engineer(self, task_id: str, *, reason: str, reassign_to: str | None = None,
                                new_agent: str | None = None, evidence: Iterable[object] = (),
                                run_id: str | None = None) -> BlockerReport:
        task = self._get_task(task_id)
        reason = _clean(reason, max_chars=4000)
        if not reason:
            raise ValueError("blocker reason is required")
        state = str(task.get("state") or "")
        if state in {TaskState.PENDING.value, TaskState.READY.value, TaskState.ASSIGNED.value,
                     TaskState.RUNNING.value, TaskState.WAITING.value, TaskState.REVIEW.value}:
            try:
                task = coordination_store.transition(task_id, TaskState.BLOCKED, failure_reason=reason, database_path=self.database_path)
            except ValueError:
                task = self._get_task(task_id)
        message = self._publish(message_type=MessageType.BLOCKER,
            subject=f"Blocked engineer task: {task.get('title', task_id)}", body=reason,
            project_id=str(task["project_id"]), task_id=task_id, run_id=run_id or task.get("run_id"),
            recipient_role="supervisor", references=_items(evidence) + (f"task:{task_id}",), topic="engineering_blocker")
        reassignment = None
        if reassign_to:
            reassignment = self.reassign_task(task_id, reassign_to, new_agent=new_agent,
                reason=f"Reassignment after blocker: {reason}", evidence=evidence, run_id=run_id)
        return BlockerReport(task_id=task_id, project_id=str(task["project_id"]), reason=reason,
            state=reassignment.state if reassignment else str(task.get("state") or state),
            escalated_to="supervisor", message_id=str(message["message_id"]), reassignment=reassignment)

    def assign_technical_task(self, task_id: str, target_role: str | None = None, **kwargs: object) -> TechnicalDelegation:
        """Compatibility name for callers that express delegation as assignment."""
        return self.delegate_task(task_id, target_role, **kwargs)

    def monitor_implementation_quality(self, project_id: str, *, limit: int = 500) -> dict[str, object]:
        """Summarize quality evidence without approving or modifying implementation."""
        tasks = coordination_store.list_tasks(project_id=project_id, limit=min(max(int(limit), 1), 500), database_path=self.database_path)
        reviews = [task for task in tasks if task.get("state") == TaskState.REVIEW.value]
        failures = [task for task in tasks if task.get("state") == TaskState.FAILED.value]
        unfinished = [task for task in tasks if task.get("state") in _ACTIVE_STATES]
        return {
            "project_id": project_id,
            "open_reviews": reviews,
            "failed_tasks": failures,
            "unfinished_tasks": unfinished,
            "quality_gates": list_quality_gates(project_id, database_path=self.database_path),
            "readiness": self.technical_readiness(project_id, limit=limit).as_dict(),
        }

    def monitor_quality(self, project_id: str, *, limit: int = 500) -> dict[str, object]:
        return self.monitor_implementation_quality(project_id, limit=limit)
    def technical_readiness(self, project_id: str, *, limit: int = 500) -> TechnicalReadiness:
        tasks = coordination_store.list_tasks(project_id=project_id, limit=min(max(int(limit), 1), 500), database_path=self.database_path)
        counts: dict[str, int] = {}
        for task in tasks:
            state = str(task.get("state") or TaskState.PENDING.value)
            counts[state] = counts.get(state, 0) + 1
        evidence: list[str] = []
        missing: list[str] = []
        failed_tests: list[str] = []
        open_reviews: list[str] = []
        blockers: list[str] = []
        completed = [task for task in tasks if task.get("state") == TaskState.COMPLETED.value]
        failed = [task for task in tasks if task.get("state") == TaskState.FAILED.value]
        for task in completed:
            evidence.append(f"completed_task:{task['id']}")
            if task.get("expected_outputs"):
                evidence.append(f"declared_outputs:{task['id']}")
        for task in failed:
            blockers.append(f"failed_task:{task['id']}")
            failed_tests.append(str(task.get("failure_reason") or task["id"]))
        for task in tasks:
            state = str(task.get("state") or "")
            if state == TaskState.REVIEW.value:
                open_reviews.append(str(task["id"]))
            elif state in {TaskState.PENDING.value, TaskState.READY.value, TaskState.ASSIGNED.value,
                           TaskState.RUNNING.value, TaskState.WAITING.value, TaskState.BLOCKED.value}:
                blockers.append(f"unfinished_task:{task['id']}")
        gates = list_quality_gates(project_id, database_path=self.database_path)
        passed_gate_names: set[str] = set()
        for gate in (item for item in gates if item.get("required")):
            name = str(gate.get("gate_name"))
            if gate.get("status") in {"passed", "waived"}:
                passed_gate_names.add(name)
                evidence.append(f"quality_gate:{name}")
            else:
                missing.append(f"quality_gate:{name}")
        tester_complete = any(task.get("role") == "tester" and task.get("state") == TaskState.COMPLETED.value for task in tasks)
        reviewer_complete = any(task.get("role") in {"reviewer", "security", "release_verifier"} and task.get("state") == TaskState.COMPLETED.value for task in tasks)
        if tasks and not tester_complete and "tests_passed" not in passed_gate_names:
            missing.append("test_evidence")
        if tasks and not reviewer_complete and "review_accepted" not in passed_gate_names:
            missing.append("review_evidence")
        if not tasks:
            missing.append("no_engineering_tasks")
        decisions = list_decisions(project_id=project_id, limit=500, database_path=self.database_path)
        evidence.append(f"technical_decisions:{len(decisions)}" if decisions else "task_state_evidence")
        blockers, missing = list(dict.fromkeys(blockers)), list(dict.fromkeys(missing))
        return TechnicalReadiness(project_id=project_id, ready=bool(tasks) and not blockers and not missing and not failed,
            task_counts=counts, evidence=tuple(evidence), missing_evidence=tuple(missing),
            failed_tests=tuple(failed_tests), open_reviews=tuple(open_reviews), blockers=tuple(blockers))

    def determine_readiness(self, project_id: str, *, limit: int = 500) -> TechnicalReadiness:
        return self.technical_readiness(project_id, limit=limit)

    def check_technical_readiness(self, project_id: str, *, limit: int = 500) -> TechnicalReadiness:
        return self.technical_readiness(project_id, limit=limit)


EngineeringManager = EngineeringManagerAgent
