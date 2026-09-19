from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.project_management import enqueue_work
from app.memory.models import MemoryLifecycle
from app.memory.sanitizer import sanitize_text
from app.memory.store import MemoryStore

from .models import Department, EmployeeStatus
from .store import ensure_employee


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


@dataclass(frozen=True)
class FailureReproduction:
    reproduction_id: str
    project_id: str
    task_id: str
    defect_id: str
    reproduction_steps: tuple[str, ...]
    expected_behavior: str
    actual_behavior: str
    logs: tuple[str, ...] = ()
    stack_trace: str = ""
    evidence: tuple[str, ...] = ()
    status: str = "reproduced"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("reproduction_steps", "logs", "evidence"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class RootCauseRecord:
    root_cause_id: str
    project_id: str
    task_id: str
    defect_id: str
    root_cause: str
    contributing_factors: tuple[str, ...]
    affected_scope: tuple[str, ...]
    evidence: tuple[str, ...]
    confidence: str = "medium"
    status: str = "diagnosed"
    memory_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("contributing_factors", "affected_scope", "evidence"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class FailureMemory:
    memory_id: str
    failure_pattern_id: str | None
    project_id: str | None
    task_id: str | None
    summary: str
    root_cause: str
    successful_fix: str | None
    lifecycle: str
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class RepairResult:
    repair_id: str
    project_id: str
    task_id: str
    defect_id: str
    root_cause_id: str | None
    repair_summary: str
    changed_files: tuple[str, ...]
    regression_tests: tuple[str, ...]
    evidence: tuple[str, ...]
    authorized: bool
    status: str
    handoff_id: str | None = None
    memory_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("changed_files", "regression_tests", "evidence"):
            result[key] = list(getattr(self, key))
        return result


class DebuggerAgent:
    """Investigate confirmed failures, make bounded authorized repairs, and return them to QA."""

    ROLE = "debugger"
    DISPLAY_NAME = "Debugger"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)
        self.memory = MemoryStore(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-debugger",
            display_name=self.DISPLAY_NAME,
            department=Department.ENGINEERING,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Debugger task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Debugger can only operate debugger tasks")
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
        topic: str = "debugging",
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

    def reproduce_failure(
        self,
        task_id: str,
        *,
        defect_id: str,
        reproduction_steps: Iterable[object],
        expected_behavior: str,
        actual_behavior: str,
        evidence: Iterable[object],
        logs: Iterable[object] = (),
        stack_trace: str = "",
        run_id: str | None = None,
    ) -> FailureReproduction:
        task = self._task(task_id)
        defect = _clean(defect_id, max_chars=128)
        steps = _items(reproduction_steps, max_chars=1000)
        expected = _clean(expected_behavior, max_chars=6000)
        actual = _clean(actual_behavior, max_chars=6000)
        refs = _items(evidence, max_chars=512)
        if not defect or not steps or not expected or not actual or not refs:
            raise ValueError("failure reproduction requires defect, steps, expected, actual and evidence")
        payload = FailureReproduction(
            reproduction_id=str(uuid4()),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            defect_id=defect,
            reproduction_steps=steps,
            expected_behavior=expected,
            actual_behavior=actual,
            logs=_items(logs, max_chars=2000),
            stack_trace=_clean(stack_trace, max_chars=8000),
            evidence=refs,
        )
        message = self._publish(
            message_type=MessageType.EVIDENCE,
            subject=f"Failure reproduced: {defect}",
            body=json.dumps(payload.as_dict(), ensure_ascii=False),
            project_id=payload.project_id,
            task_id=payload.task_id,
            run_id=run_id or task.get("run_id"),
            references=refs + (f"defect:{defect}",),
            topic="failure_reproduction",
        )
        return FailureReproduction(**{**asdict(payload), "message_id": str(message["message_id"])})

    reproduce = reproduce_failure

    def record_root_cause(
        self,
        task_id: str,
        *,
        defect_id: str,
        root_cause: str,
        evidence: Iterable[object],
        contributing_factors: Iterable[object] = (),
        affected_scope: Iterable[object] = (),
        confidence: str = "medium",
        run_id: str | None = None,
    ) -> RootCauseRecord:
        task = self._task(task_id)
        defect = _clean(defect_id, max_chars=128)
        cause = _clean(root_cause, max_chars=6000)
        refs = _items(evidence, max_chars=512)
        if not defect or not cause or not refs:
            raise ValueError("root cause record requires defect, cause and evidence")
        cause_id = str(uuid4())
        memory = self.memory.capture_failure(
            project_id=str(task["project_id"]),
            role=self.ROLE,
            title=f"Debugger failure pattern: {defect}",
            reason=cause,
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            evidence=({"type": "root_cause", "summary": item} for item in refs),
        )
        payload = RootCauseRecord(
            root_cause_id=cause_id,
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            defect_id=defect,
            root_cause=cause,
            contributing_factors=_items(contributing_factors),
            affected_scope=_items(affected_scope, max_chars=512),
            evidence=refs,
            confidence=_clean(confidence, max_chars=32).casefold() or "medium",
            memory_id=str(memory["id"]),
        )
        message = self._publish(
            message_type=MessageType.EVIDENCE,
            subject=f"Root cause diagnosed: {defect}",
            body=json.dumps(payload.as_dict(), ensure_ascii=False),
            project_id=payload.project_id,
            task_id=payload.task_id,
            run_id=run_id or task.get("run_id"),
            references=refs + (f"memory:{payload.memory_id}",),
            topic="root_cause",
        )
        return RootCauseRecord(**{**asdict(payload), "message_id": str(message["message_id"])})

    diagnose = record_root_cause

    def create_failure_memory(
        self,
        task_id: str,
        *,
        title: str,
        root_cause: str,
        evidence: Iterable[object],
        successful_fix: str | None = None,
        run_id: str | None = None,
    ) -> FailureMemory:
        task = self._task(task_id)
        refs = _items(evidence, max_chars=512)
        cause = _clean(root_cause, max_chars=2000)
        clean_title = _clean(title, max_chars=256)
        if not clean_title or not cause or not refs:
            raise ValueError("failure memory requires title, root cause and evidence")
        memory = self.memory.capture_failure(
            project_id=str(task["project_id"]),
            role=self.ROLE,
            title=clean_title,
            reason=cause,
            successful_fix=_clean(successful_fix, max_chars=2000) or None,
            run_id=run_id or task.get("run_id"),
            task_id=str(task["id"]),
            evidence=({"type": "debugger", "summary": item} for item in refs),
        )
        return FailureMemory(
            memory_id=str(memory["id"]),
            failure_pattern_id=memory.get("failure_pattern_id"),
            project_id=memory.get("project_id"),
            task_id=memory.get("task_id"),
            summary=str(memory.get("summary") or clean_title),
            root_cause=cause,
            successful_fix=_clean(successful_fix, max_chars=2000) or None,
            lifecycle=str(memory.get("lifecycle") or "candidate"),
            evidence=refs,
        )

    capture_failure_memory = create_failure_memory

    def promote_failure_memory(
        self,
        memory_id: str,
        *,
        evidence: Iterable[object],
        target: str | MemoryLifecycle = MemoryLifecycle.VALIDATED,
    ) -> FailureMemory:
        refs = _items(evidence, max_chars=512)
        if not refs:
            raise ValueError("failure memory promotion requires verification evidence")
        promoted = self.memory.promote(
            _clean(memory_id, max_chars=128),
            evidence=({"type": "verification", "summary": item} for item in refs),
            target=target,
        )
        content = promoted.get("content") if isinstance(promoted.get("content"), dict) else {}
        return FailureMemory(
            memory_id=str(promoted["id"]),
            failure_pattern_id=promoted.get("failure_pattern_id"),
            project_id=promoted.get("project_id"),
            task_id=promoted.get("task_id"),
            summary=str(promoted.get("summary") or "Failure pattern"),
            root_cause=str(content.get("root_cause") or ""),
            successful_fix=content.get("successful_fix"),
            lifecycle=str(promoted.get("lifecycle") or "validated"),
            evidence=refs,
        )

    def repair_failure(
        self,
        task_id: str,
        *,
        defect_id: str,
        repair_summary: str | None = None,
        changed_files: Iterable[object] = (),
        regression_tests: Iterable[object] = (),
        evidence: Iterable[object] = (),
        authorized: bool = False,
        root_cause_id: str | None = None,
        memory_id: str | None = None,
        run_id: str | None = None,
    ) -> RepairResult:
        task = self._task(task_id)
        if not authorized:
            raise PermissionError("Debugger repair requires explicit authorization")
        defect = _clean(defect_id, max_chars=128)
        summary = _clean(repair_summary, max_chars=6000)
        files = _items(changed_files, max_chars=512)
        tests = _items(regression_tests, max_chars=1000)
        refs = _items(evidence, max_chars=512)
        if not defect or not summary or not files or not tests or not refs:
            raise ValueError("authorized repair requires defect, summary, files, regression tests and evidence")
        repair_id = str(uuid4())
        payload = RepairResult(
            repair_id=repair_id,
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            defect_id=defect,
            root_cause_id=_clean(root_cause_id, max_chars=128) or None,
            repair_summary=summary,
            changed_files=files,
            regression_tests=tests,
            evidence=refs,
            authorized=True,
            status="ready_for_test",
            memory_id=_clean(memory_id, max_chars=128) or None,
        )
        message = self._publish(
            message_type=MessageType.RESULT,
            subject=f"Repair ready for verification: {defect}",
            body=json.dumps(payload.as_dict(), ensure_ascii=False),
            project_id=payload.project_id,
            task_id=payload.task_id,
            run_id=run_id or task.get("run_id"),
            recipient_role="tester",
            references=refs + (f"defect:{defect}",),
            topic="repair_ready_for_test",
        )
        handoff = AgentHandoff(
            sender_role=self.ROLE,
            recipient_role="tester",
            summary=f"Verify debugger repair: {defect}",
            completed=("Failure root cause was diagnosed.", "A bounded repair was authorized and recorded.",),
            artifacts=("RepairResult", "regression_tests", "evidence"),
            changed_files=files,
            decisions=(summary,),
            risks=("Repair remains unverified until Tester reruns the regression suite.",),
            remaining_work=("Run independent regression tests and acceptance verification.",),
            verification=refs + tests,
            run_id=run_id or task.get("run_id"),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
        )
        handoff_row = self.handoffs.submit(handoff)
        self._publish(
            message_type=MessageType.HANDOFF,
            subject=handoff.summary,
            body=json.dumps({"handoff": handoff_row, "repair": payload.as_dict()}, ensure_ascii=False),
            project_id=payload.project_id,
            task_id=payload.task_id,
            run_id=run_id or task.get("run_id"),
            recipient_role="tester",
            references=(f"handoff:{handoff_row['handoff_id']}", f"repair:{repair_id}"),
            topic="repair_handoff",
        )
        enqueue_work("tester", payload.project_id, "repair_verification", repair_id, task_id=payload.task_id, priority=int(task.get("priority") or 50), database_path=self.database_path)
        return RepairResult(**{**asdict(payload), "handoff_id": str(handoff_row["handoff_id"]), "message_id": str(message["message_id"])})

    repair = repair_failure
    record_repair = repair_failure


Debugger = DebuggerAgent
DebugAgent = DebuggerAgent


__all__ = [
    "DebugAgent",
    "Debugger",
    "DebuggerAgent",
    "FailureMemory",
    "FailureReproduction",
    "RepairResult",
    "RootCauseRecord",
]

