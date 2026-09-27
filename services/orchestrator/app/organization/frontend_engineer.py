from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType, TaskState
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
            raise ValueError("frontend resource scope must be project-relative")
        resources.append(item)
        if len(resources) >= limit:
            break
    return tuple(resources)


def _handoff_target(value: object) -> str:
    target = _clean(value, max_chars=128).casefold()
    if target not in _HANDOFF_TARGETS:
        raise ValueError("frontend handoffs must target integration or tester")
    return target


@dataclass(frozen=True)
class FrontendImplementationPlan:
    plan_id: str
    task_id: str
    project_id: str
    ux_spec_refs: tuple[str, ...] = ()
    architecture_refs: tuple[str, ...] = ()
    api_contracts: tuple[dict[str, object], ...] = ()
    routing: tuple[str, ...] = ()
    state_management: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()
    accessibility: tuple[str, ...] = ()
    responsive_rules: tuple[str, ...] = ()
    conventions: tuple[str, ...] = ()
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
            "ux_spec_refs",
            "architecture_refs",
            "routing",
            "state_management",
            "forms",
            "accessibility",
            "responsive_rules",
            "conventions",
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
class APIClarificationRequest:
    request_id: str
    project_id: str
    task_id: str
    subject: str
    question: str
    expected_contract: str = ""
    evidence: tuple[str, ...] = ()
    recipient_role: str = "backend"
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class FrontendIntegrationIssue:
    issue_id: str
    project_id: str
    task_id: str
    subject: str
    frontend_expectation: str
    backend_contract: str
    evidence: tuple[str, ...] = ()
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class FrontendClaim:
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
class FrontendImplementationResult:
    task_id: str
    project_id: str
    status: str
    ux_spec_refs: tuple[str, ...] = ()
    api_contracts_used: tuple[dict[str, object], ...] = ()
    code_changes: tuple[str, ...] = ()
    files_changed: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    technical_notes: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    handoff_ids: tuple[str, ...] = ()
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("ux_spec_refs", "code_changes", "files_changed", "tests", "technical_notes", "verification", "handoff_ids"):
            result[key] = list(getattr(self, key))
        result["api_contracts_used"] = list(self.api_contracts_used)
        return result


class FrontendEngineerAgent:
    """Scoped frontend implementer that consumes UX/API contracts and hands off verification."""

    ROLE = "frontend"
    DISPLAY_NAME = "Frontend Engineer"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-frontend",
            display_name=self.DISPLAY_NAME,
            department=Department.ENGINEERING,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Frontend task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Frontend Engineer can only operate frontend tasks")
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
        topic: str = "frontend_engineering",
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
        ux_spec_refs: Iterable[object] = (),
        architecture_refs: Iterable[object] = (),
        api_contracts: Iterable[object] = (),
        routing: Iterable[object] = (),
        state_management: Iterable[object] = (),
        forms: Iterable[object] = (),
        accessibility: Iterable[object] = (),
        responsive_rules: Iterable[object] = (),
        conventions: Iterable[object] = (),
        scope: Iterable[object] | None = None,
        acceptance_criteria: Iterable[object] = (),
        test_plan: Iterable[object] = (),
        inspection_evidence: Iterable[object] = (),
        handoff_targets: Iterable[object] = ("integration", "tester"),
        run_id: str | None = None,
    ) -> FrontendImplementationPlan:
        """Create a plan only after consuming a UX handoff and inspecting the current code."""
        task = self._task(task_id)
        ux_refs = _items(ux_spec_refs, max_chars=500)
        if not ux_refs:
            raise ValueError("frontend implementation requires a UX/design handoff")
        evidence = _items(inspection_evidence, max_chars=500)
        if not evidence:
            raise ValueError("relevant existing-code inspection evidence is required before frontend work")
        resources = _resources(scope if scope is not None else task.get("scope") or ())
        if not resources:
            raise ValueError("frontend implementation requires a non-empty scoped workspace")
        targets = tuple(dict.fromkeys(_handoff_target(item) for item in handoff_targets))
        if not targets:
            raise ValueError("frontend implementation requires an integration or tester handoff")
        plan = FrontendImplementationPlan(
            plan_id=str(uuid4()),
            task_id=str(task["id"]),
            project_id=str(task["project_id"]),
            ux_spec_refs=ux_refs,
            architecture_refs=_items(architecture_refs, max_chars=500),
            api_contracts=_mapping_items(api_contracts),
            routing=_items(routing),
            state_management=_items(state_management),
            forms=_items(forms),
            accessibility=_items(accessibility),
            responsive_rules=_items(responsive_rules),
            conventions=_items(conventions),
            scope=resources,
            acceptance_criteria=_items(acceptance_criteria),
            test_plan=_items(test_plan),
            inspection_evidence=evidence,
            handoff_targets=targets,
        )
        message = self._publish(
            message_type=MessageType.STATUS,
            subject=f"Frontend plan: {task.get('title', task_id)}",
            body=json.dumps(plan.as_dict(), ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=ux_refs + evidence + tuple(f"architecture:{item}" for item in plan.architecture_refs),
            topic="frontend_plan",
        )
        return FrontendImplementationPlan(**{**asdict(plan), "message_id": str(message["message_id"])})

    def request_backend_clarification(
        self,
        task_id: str,
        subject: str,
        question: str,
        *,
        expected_contract: str = "",
        evidence: Iterable[object] = (),
        run_id: str | None = None,
    ) -> APIClarificationRequest:
        task = self._task(task_id)
        clean_subject = _clean(subject, max_chars=500)
        clean_question = _clean(question, max_chars=4000)
        if not clean_subject or not clean_question:
            raise ValueError("backend clarification requires a subject and question")
        refs = _items(evidence, max_chars=512)
        payload = {
            "request_id": str(uuid4()),
            "subject": clean_subject,
            "question": clean_question,
            "expected_contract": _clean(expected_contract, max_chars=4000),
            "evidence": list(refs),
        }
        message = self._publish(
            message_type=MessageType.QUESTION,
            subject=clean_subject,
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role="backend",
            references=refs,
            topic="frontend_api_question",
        )
        return APIClarificationRequest(
            request_id=payload["request_id"],
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            subject=clean_subject,
            question=clean_question,
            expected_contract=payload["expected_contract"],
            evidence=refs,
            message_id=str(message["message_id"]),
        )

    ask_backend = request_backend_clarification

    def raise_integration_issue(
        self,
        task_id: str,
        subject: str,
        frontend_expectation: str,
        backend_contract: str,
        *,
        evidence: Iterable[object] = (),
        run_id: str | None = None,
    ) -> FrontendIntegrationIssue:
        task = self._task(task_id)
        values = tuple(_clean(value, max_chars=6000) for value in (subject, frontend_expectation, backend_contract))
        if not all(values):
            raise ValueError("frontend integration issue requires subject, expectation and backend contract")
        refs = _items(evidence, max_chars=512)
        payload = {
            "issue_id": str(uuid4()),
            "subject": values[0],
            "frontend_expectation": values[1],
            "backend_contract": values[2],
            "evidence": list(refs),
        }
        message = self._publish(
            message_type=MessageType.BLOCKER,
            subject=values[0],
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role="integration",
            references=refs,
            topic="frontend_integration_issue",
        )
        return FrontendIntegrationIssue(
            issue_id=payload["issue_id"],
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            subject=values[0],
            frontend_expectation=values[1],
            backend_contract=values[2],
            evidence=refs,
            message_id=str(message["message_id"]),
        )

    report_integration_issue = raise_integration_issue

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
        agent_id: str = "employee-frontend",
        lease_seconds: int = 1800,
        run_id: str | None = None,
    ) -> FrontendClaim:
        """Claim a frontend task only after dependencies and workspace locks are safe."""
        self.ensure_profile()
        task = self._task(task_id)
        task_resources = _resources(resources if resources is not None else task.get("scope") or ())
        if not task_resources:
            raise ValueError("frontend task claim requires a non-empty workspace scope")
        previous = str(task.get("state") or TaskState.PENDING.value)
        ready, blocked = self._dependencies_ready(str(task["id"]))
        if not ready:
            if previous in {TaskState.PENDING.value, TaskState.READY.value}:
                task = coordination_store.transition(str(task["id"]), TaskState.BLOCKED, failure_reason="Incomplete frontend dependencies: " + ", ".join(blocked), database_path=self.database_path)
            message = self._publish(
                message_type=MessageType.BLOCKER,
                subject=f"Frontend task blocked: {task.get('title', task_id)}",
                body="Incomplete dependencies: " + ", ".join(blocked),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                recipient_role="engineering_manager",
                references=tuple(f"task:{item}" for item in blocked),
                topic="frontend_blocker",
            )
            return FrontendClaim(str(task["id"]), str(task["project_id"]), agent_id, task_resources, previous, str(task["state"]), False, blocked, str(message["message_id"]), "blocked")
        acquired: list[str] = []
        for resource in task_resources:
            if not coordination_store.acquire_lock(resource, str(task["id"]), self.ROLE, lease_seconds=lease_seconds, database_path=self.database_path):
                for locked in acquired:
                    coordination_store.release_lock(locked, str(task["id"]), database_path=self.database_path)
                if previous in {TaskState.PENDING.value, TaskState.READY.value}:
                    task = coordination_store.transition(str(task["id"]), TaskState.BLOCKED, failure_reason=f"Workspace resource is locked: {resource}", database_path=self.database_path)
                message = self._publish(
                    message_type=MessageType.BLOCKER,
                    subject=f"Frontend workspace conflict: {task.get('title', task_id)}",
                    body=f"Workspace resource is locked: {resource}",
                    project_id=str(task["project_id"]),
                    task_id=str(task["id"]),
                    run_id=run_id or task.get("run_id"),
                    recipient_role="engineering_manager",
                    references=(f"resource:{resource}",),
                    topic="frontend_blocker",
                )
                return FrontendClaim(str(task["id"]), str(task["project_id"]), agent_id, task_resources, previous, str(task["state"]), False, (resource,), str(message["message_id"]), "blocked")
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
            raise ValueError("frontend task is already assigned to another agent")
        if current == TaskState.ASSIGNED.value:
            task = coordination_store.transition(str(task["id"]), TaskState.RUNNING, assigned_agent=agent_id, database_path=self.database_path)
            current = str(task["state"])
        elif current != TaskState.RUNNING.value:
            for locked in acquired:
                coordination_store.release_lock(locked, str(task["id"]), database_path=self.database_path)
            raise ValueError(f"frontend task is not claimable from state: {current}")
        message = self._publish(
            message_type=MessageType.STATUS,
            subject=f"Frontend task claimed: {task.get('title', task_id)}",
            body=json.dumps({"agent_id": agent_id, "resources": list(task_resources), "state": current}, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=tuple(f"resource:{item}" for item in task_resources),
            topic="frontend_execution",
        )
        return FrontendClaim(str(task["id"]), str(task["project_id"]), agent_id, task_resources, previous, current, True, (), str(message["message_id"]), "claimed")

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
        ux_spec_refs: Iterable[object] = (),
        api_contracts_used: Iterable[object] = (),
        code_changes: Iterable[object] = (),
        files_changed: Iterable[object] = (),
        tests: Iterable[object] = (),
        technical_notes: Iterable[object] = (),
        verification: Iterable[object] = (),
        handoff_targets: Iterable[object] = ("integration", "tester"),
        run_id: str | None = None,
    ) -> FrontendImplementationResult:
        """Record evidence and hand work to Integration/QA; never self-approves completion."""
        task = self._task(task_id)
        state = str(task.get("state") or "")
        if state == TaskState.ASSIGNED.value:
            task = coordination_store.transition(str(task["id"]), TaskState.RUNNING, database_path=self.database_path)
            state = TaskState.RUNNING.value
        if state != TaskState.RUNNING.value:
            raise ValueError(f"frontend result requires a running task, not {state}")
        ux_refs = _items(ux_spec_refs, max_chars=500)
        code = _items(code_changes, max_chars=4000)
        tests_run = _items(tests, max_chars=1000)
        verification_items = _items(verification, max_chars=500)
        if not ux_refs:
            raise ValueError("frontend result must reference the consumed UX/design handoff")
        if not code:
            raise ValueError("frontend result must include code changes")
        if not tests_run and not verification_items:
            raise ValueError("frontend result requires test or verification evidence")
        targets = tuple(dict.fromkeys(_handoff_target(item) for item in handoff_targets))
        changed = _resources(files_changed)
        notes = _items(technical_notes)
        contracts = _mapping_items(api_contracts_used)
        payload = {
            "task_id": str(task["id"]),
            "project_id": str(task["project_id"]),
            "ux_spec_refs": list(ux_refs),
            "api_contracts_used": list(contracts),
            "code_changes": list(code),
            "files_changed": list(changed),
            "tests": list(tests_run),
            "technical_notes": list(notes),
            "verification": list(verification_items),
            "handoff_targets": list(targets),
        }
        result_message = self._publish(
            message_type=MessageType.RESULT,
            subject=f"Frontend implementation result: {task.get('title', task_id)}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=ux_refs + tuple(f"file:{item}" for item in changed),
            topic="frontend_result",
        )
        task = coordination_store.transition(str(task["id"]), TaskState.REVIEW, database_path=self.database_path)
        handoff_ids: list[str] = []
        for target in targets:
            handoff = AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target,
                summary=f"Frontend implementation: {task.get('title', task_id)}",
                completed=("Frontend behavior implemented from the UX/design handoff.", "API contracts were consumed without invention.", "Independent integration and QA verification is required."),
                artifacts=("ux_spec_refs", "api_contracts_used", "code_changes", "tests", "technical_notes"),
                changed_files=changed,
                decisions=tuple(f"api:{item}" for item in contracts),
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
                topic="frontend_handoff",
            )
            enqueue_work(target, str(task["project_id"]), "handoff", str(row["handoff_id"]), task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        self.release_locks(str(task["id"]), task.get("scope") or changed)
        return FrontendImplementationResult(str(task["id"]), str(task["project_id"]), TaskState.REVIEW.value, ux_refs, contracts, code, changed, tests_run, notes, verification_items, tuple(handoff_ids), str(result_message["message_id"]))

    def complete(self, *args: object, **kwargs: object) -> FrontendImplementationResult:
        return self.record_result(*args, **kwargs)


FrontendEngineer = FrontendEngineerAgent


__all__ = [
    "APIClarificationRequest",
    "FrontendClaim",
    "FrontendEngineer",
    "FrontendEngineerAgent",
    "FrontendImplementationPlan",
    "FrontendImplementationResult",
    "FrontendIntegrationIssue",
]
