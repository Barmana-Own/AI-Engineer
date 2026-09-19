from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.project_management import enqueue_work
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_REPAIR_TARGETS = frozenset({"debugger", "backend", "frontend", "integration", "implementer", "architect", "engineering_manager"})


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
                    item[clean_key] = {str(k): _clean(v, max_chars=4000) if not isinstance(v, (list, tuple, dict)) else v for k, v in raw.items()}
                elif isinstance(raw, (list, tuple, set)):
                    item[clean_key] = [_clean(entry, max_chars=2000) if not isinstance(entry, Mapping) else dict(entry) for entry in raw]
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


def _owner_role(value: object) -> str:
    role = _clean(value or "debugger", max_chars=128).casefold()
    if role not in _REPAIR_TARGETS:
        raise ValueError("tester defects must target a debugger or responsible engineering role")
    return role


@dataclass(frozen=True)
class TestPlan:
    plan_id: str
    project_id: str
    task_id: str
    acceptance_criteria: tuple[str, ...]
    test_cases: tuple[dict[str, object], ...]
    fixtures: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    inspection_evidence: tuple[str, ...] = ()
    status: str = "planned"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("acceptance_criteria", "fixtures", "scope", "inspection_evidence"):
            result[key] = list(getattr(self, key))
        result["test_cases"] = list(self.test_cases)
        return result


@dataclass(frozen=True)
class DefectReport:
    defect_id: str
    project_id: str
    task_id: str
    test_name: str
    severity: str
    reproduction_steps: tuple[str, ...]
    expected_behavior: str
    actual_behavior: str
    evidence: tuple[str, ...]
    affected_files: tuple[str, ...] = ()
    owner_role: str = "debugger"
    status: str = "open"
    handoff_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        for key in ("reproduction_steps", "evidence", "affected_files"):
            result[key] = list(getattr(self, key))
        return result


@dataclass(frozen=True)
class RepairLoop:
    loop_id: str
    defect_id: str
    project_id: str
    task_id: str
    owner_role: str
    passed: bool
    tests: tuple[str, ...]
    evidence: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["tests"] = list(self.tests)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class RegressionVerification:
    verification_id: str
    project_id: str
    task_id: str
    passed: bool
    tests: tuple[str, ...]
    evidence: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["tests"] = list(self.tests)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class AcceptanceCriteriaVerification:
    verification_id: str
    project_id: str
    task_id: str
    passed_criteria: tuple[str, ...]
    failed_criteria: tuple[str, ...]
    evidence: tuple[str, ...]
    status: str
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["passed_criteria"] = list(self.passed_criteria)
        result["failed_criteria"] = list(self.failed_criteria)
        result["evidence"] = list(self.evidence)
        return result


class TestEngineerAgent:
    """Independent QA agent that records evidence and routes production fixes."""

    ROLE = "tester"
    DISPLAY_NAME = "QA / Test Engineer"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-tester",
            display_name=self.DISPLAY_NAME,
            department=Department.QUALITY,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Tester task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("QA/Test Engineer can only operate tester tasks")
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
        topic: str = "qa_testing",
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

    def create_test_plan(
        self,
        task_id: str,
        *,
        acceptance_criteria: Iterable[object],
        test_cases: Iterable[object],
        fixtures: Iterable[object] = (),
        scope: Iterable[object] = (),
        inspection_evidence: Iterable[object] = (),
        run_id: str | None = None,
    ) -> TestPlan:
        task = self._task(task_id)
        criteria = _items(acceptance_criteria)
        cases = _mapping_items(test_cases)
        if not criteria or not cases:
            raise ValueError("test plan requires acceptance criteria and test cases")
        evidence = _items(inspection_evidence, max_chars=500)
        plan = TestPlan(
            plan_id=str(uuid4()),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            acceptance_criteria=criteria,
            test_cases=cases,
            fixtures=_items(fixtures),
            scope=_items(scope, max_chars=512),
            inspection_evidence=evidence,
        )
        message = self._publish(
            message_type=MessageType.STATUS,
            subject=f"Test plan: {task.get('title', task_id)}",
            body=json.dumps(plan.as_dict(), ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=evidence,
            topic="test_plan",
        )
        return TestPlan(**{**asdict(plan), "message_id": str(message["message_id"])})

    plan = create_test_plan

    def record_failure(
        self,
        task_id: str,
        *,
        test_name: str,
        reproduction_steps: Iterable[object],
        expected_behavior: str,
        actual_behavior: str,
        evidence: Iterable[object],
        affected_files: Iterable[object] = (),
        severity: str = "high",
        owner_role: str = "debugger",
        run_id: str | None = None,
    ) -> DefectReport:
        """Persist a reproducible defect and hand production repair to its owner."""
        task = self._task(task_id)
        name = _clean(test_name, max_chars=500)
        steps = _items(reproduction_steps, max_chars=1000)
        expected = _clean(expected_behavior, max_chars=6000)
        actual = _clean(actual_behavior, max_chars=6000)
        refs = _items(evidence, max_chars=512)
        if not name or not steps or not expected or not actual or not refs:
            raise ValueError("defect report requires test, reproduction, expected, actual and evidence")
        target = _owner_role(owner_role)
        defect_id = str(uuid4())
        files = _items(affected_files, max_chars=512)
        payload = {
            "defect_id": defect_id,
            "test_name": name,
            "severity": _clean(severity, max_chars=64).casefold() or "high",
            "reproduction_steps": list(steps),
            "expected_behavior": expected,
            "actual_behavior": actual,
            "evidence": list(refs),
            "affected_files": list(files),
            "owner_role": target,
        }
        message = self._publish(
            message_type=MessageType.BLOCKER,
            subject=f"Defect: {name}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=target,
            references=refs + (f"defect:{defect_id}",),
            topic="defect_report",
        )
        handoff = AgentHandoff(
            sender_role=self.ROLE,
            recipient_role=target,
            summary=f"Repair defect: {name}",
            completed=("Failure was reproduced independently.", "Expected and actual behavior are recorded.", "Production code was not modified by QA."),
            artifacts=("DefectReport", "evidence", "reproduction_steps"),
            changed_files=files,
            decisions=(expected, actual),
            risks=(f"Severity: {payload['severity']}",),
            remaining_work=("Repair the root cause and return the task for QA rerun.",),
            verification=refs,
            run_id=run_id or task.get("run_id"),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
        )
        handoff_row = self.handoffs.submit(handoff)
        self._publish(
            message_type=MessageType.HANDOFF,
            subject=handoff.summary,
            body=json.dumps({"handoff": handoff_row, "defect": payload}, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=target,
            references=(f"handoff:{handoff_row['handoff_id']}", f"defect:{defect_id}"),
            topic="defect_handoff",
        )
        enqueue_work(target, str(task["project_id"]), "defect", defect_id, task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        return DefectReport(
            defect_id=defect_id,
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            test_name=name,
            severity=payload["severity"],
            reproduction_steps=steps,
            expected_behavior=expected,
            actual_behavior=actual,
            evidence=refs,
            affected_files=files,
            owner_role=target,
            handoff_id=str(handoff_row["handoff_id"]),
            message_id=str(message["message_id"]),
        )

    report_failure = record_failure
    handoff_defect = record_failure

    def verify_repair(
        self,
        task_id: str,
        defect_id: str,
        *,
        passed: bool,
        tests: Iterable[object],
        evidence: Iterable[object],
        owner_role: str = "debugger",
        run_id: str | None = None,
    ) -> RepairLoop:
        task = self._task(task_id)
        test_items = _items(tests, max_chars=1000)
        refs = _items(evidence, max_chars=512)
        if not _clean(defect_id, max_chars=128) or not test_items or not refs:
            raise ValueError("repair verification requires defect id, rerun tests and evidence")
        status = "verified" if passed else "failed"
        payload = {
            "loop_id": str(uuid4()),
            "defect_id": _clean(defect_id, max_chars=128),
            "passed": bool(passed),
            "tests": list(test_items),
            "evidence": list(refs),
            "status": status,
        }
        message = self._publish(
            message_type=MessageType.RESULT if passed else MessageType.BLOCKER,
            subject=f"Repair verification: {payload['defect_id']}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=_owner_role(owner_role),
            references=refs + (f"defect:{payload['defect_id']}",),
            topic="repair_verification",
        )
        return RepairLoop(payload["loop_id"], payload["defect_id"], str(task["project_id"]), str(task["id"]), _owner_role(owner_role), bool(passed), test_items, refs, status, str(message["message_id"]))

    rerun_after_fix = verify_repair

    def verify_regression(
        self,
        task_id: str,
        *,
        passed: bool,
        tests: Iterable[object],
        evidence: Iterable[object],
        run_id: str | None = None,
    ) -> RegressionVerification:
        task = self._task(task_id)
        test_items = _items(tests, max_chars=1000)
        refs = _items(evidence, max_chars=512)
        if not test_items or not refs:
            raise ValueError("regression verification requires tests and evidence")
        status = "passed" if passed else "failed"
        payload = {"verification_id": str(uuid4()), "passed": bool(passed), "tests": list(test_items), "evidence": list(refs), "status": status}
        message = self._publish(
            message_type=MessageType.RESULT if passed else MessageType.BLOCKER,
            subject=f"Regression verification: {task.get('title', task_id)}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=refs,
            topic="regression_verification",
        )
        return RegressionVerification(payload["verification_id"], str(task["project_id"]), str(task["id"]), bool(passed), test_items, refs, status, str(message["message_id"]))

    regression = verify_regression

    def verify_acceptance_criteria(
        self,
        task_id: str,
        criteria: Mapping[object, object] | Iterable[object],
        *,
        evidence: Iterable[object],
        run_id: str | None = None,
    ) -> AcceptanceCriteriaVerification:
        task = self._task(task_id)
        passed: list[str] = []
        failed: list[str] = []
        if isinstance(criteria, Mapping):
            pairs = criteria.items()
        else:
            pairs = ((item.get("criterion"), item.get("passed")) if isinstance(item, Mapping) else (item, False) for item in criteria)
        for criterion, result in pairs:
            name = _clean(criterion, max_chars=1000)
            if not name:
                continue
            (passed if bool(result) else failed).append(name)
        refs = _items(evidence, max_chars=512)
        if not (passed or failed) or not refs:
            raise ValueError("acceptance verification requires criteria results and evidence")
        status = "passed" if not failed else "failed"
        payload = {"verification_id": str(uuid4()), "passed_criteria": passed, "failed_criteria": failed, "evidence": list(refs), "status": status}
        message = self._publish(
            message_type=MessageType.RESULT if not failed else MessageType.BLOCKER,
            subject=f"Acceptance criteria verification: {task.get('title', task_id)}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=refs,
            topic="acceptance_verification",
        )
        return AcceptanceCriteriaVerification(payload["verification_id"], str(task["project_id"]), str(task["id"]), tuple(passed), tuple(failed), refs, status, str(message["message_id"]))

    verify_acceptance = verify_acceptance_criteria


QAEngineerAgent = TestEngineerAgent
TesterAgent = TestEngineerAgent
TestEngineer = TestEngineerAgent


__all__ = [
    "AcceptanceCriteriaVerification",
    "DefectReport",
    "QAEngineerAgent",
    "RegressionVerification",
    "RepairLoop",
    "TestEngineer",
    "TestEngineerAgent",
    "TesterAgent",
    "TestPlan",
]
