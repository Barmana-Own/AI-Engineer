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


_REVISION_TARGETS = frozenset({"backend", "frontend", "architect", "configuration", "project_manager", "engineering_manager"})


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


def _contract_value(contract: Mapping[str, object], key: str) -> object:
    for candidate in (key, key.replace("_", "-"), key.replace("_", "")):
        if candidate in contract:
            return contract[candidate]
    return None


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _canonical(raw) for key, raw in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set)):
        return [_canonical(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return value


def _owner_role(value: object) -> str:
    role = _clean(value, max_chars=128).casefold()
    if role not in _REVISION_TARGETS:
        raise ValueError("integration revisions must target a responsible engineering role")
    return role


@dataclass(frozen=True)
class ContractMismatch:
    mismatch_id: str
    project_id: str
    task_id: str
    boundary: str
    field: str
    expected: object
    actual: object
    owner_role: str
    severity: str = "high"
    evidence: tuple[str, ...] = ()
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class IntegrationFailure:
    failure_id: str
    project_id: str
    task_id: str
    boundary: str
    reason: str
    owner_role: str | None = None
    evidence: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    status: str = "open"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        result["tests"] = list(self.tests)
        return result


@dataclass(frozen=True)
class RevisionRequest:
    request_id: str
    project_id: str
    task_id: str
    owner_role: str
    subject: str
    reason: str
    mismatch_id: str | None = None
    requested_changes: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    status: str = "open"
    handoff_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["requested_changes"] = list(self.requested_changes)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class IntegrationSuccess:
    success_id: str
    project_id: str
    task_id: str
    checks: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    status: str = "passed"
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["checks"] = list(self.checks)
        result["tests"] = list(self.tests)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class IntegrationReport:
    report_id: str
    project_id: str
    task_id: str
    status: str
    contract_mismatches: tuple[ContractMismatch, ...] = ()
    failures: tuple[IntegrationFailure, ...] = ()
    checks: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    revision_request_ids: tuple[str, ...] = ()
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["contract_mismatches"] = [item.as_dict() for item in self.contract_mismatches]
        result["failures"] = [item.as_dict() for item in self.failures]
        result["checks"] = list(self.checks)
        result["tests"] = list(self.tests)
        result["evidence"] = list(self.evidence)
        result["revision_request_ids"] = list(self.revision_request_ids)
        return result


class IntegrationEngineerAgent:
    """Independent boundary verifier that diagnoses and routes integration work."""

    ROLE = "integration"
    DISPLAY_NAME = "Integration Engineer"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id="employee-integration",
            display_name=self.DISPLAY_NAME,
            department=Department.ENGINEERING,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Integration task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Integration Engineer can only operate integration tasks")
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
        topic: str = "integration_engineering",
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

    def request_revision(
        self,
        task_id: str,
        mismatch: ContractMismatch | Mapping[str, object] | str,
        owner_role: str | None = None,
        *,
        requested_changes: Iterable[object] = (),
        evidence: Iterable[object] = (),
        run_id: str | None = None,
    ) -> RevisionRequest:
        """Route a diagnosed boundary defect to its owner instead of editing it blindly."""
        task = self._task(task_id)
        if isinstance(mismatch, ContractMismatch):
            mismatch_data = mismatch.as_dict()
        elif isinstance(mismatch, Mapping):
            mismatch_data = dict(mismatch)
        else:
            mismatch_data = {"reason": _clean(mismatch)}
        target = _owner_role(owner_role or mismatch_data.get("owner_role") or "backend")
        subject = _clean(mismatch_data.get("subject") or mismatch_data.get("boundary") or "Integration contract revision", max_chars=500)
        reason = _clean(mismatch_data.get("reason") or f"{mismatch_data.get('field', 'contract')} differs across the integration boundary", max_chars=6000)
        if not subject or not reason:
            raise ValueError("integration revision requires a subject and reason")
        refs = _items(evidence or mismatch_data.get("evidence") or (), max_chars=512)
        changes = _items(requested_changes, max_chars=2000)
        request_id = str(uuid4())
        payload = {
            "request_id": request_id,
            "owner_role": target,
            "subject": subject,
            "reason": reason,
            "mismatch_id": mismatch_data.get("mismatch_id"),
            "requested_changes": list(changes),
            "evidence": list(refs),
        }
        message = self._publish(
            message_type=MessageType.REVISION_REQUEST,
            subject=subject,
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=target,
            references=refs + ((f"mismatch:{mismatch_data['mismatch_id']}",) if mismatch_data.get("mismatch_id") else ()),
            topic="integration_revision_request",
        )
        handoff = AgentHandoff(
            sender_role=self.ROLE,
            recipient_role=target,
            summary=f"Integration revision: {subject}",
            completed=("Boundary failure was reproduced or diagnosed.", "Integration Engineer did not modify the owning component."),
            artifacts=("contract_mismatch", "integration_failure", "evidence"),
            changed_files=(),
            decisions=(reason,),
            risks=("Cross-component behavior remains unverified until the owner responds.",),
            remaining_work=changes or ("Update the owning contract or implementation and rerun integration verification.",),
            verification=refs,
            run_id=run_id or task.get("run_id"),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
        )
        handoff_row = self.handoffs.submit(handoff)
        self._publish(
            message_type=MessageType.HANDOFF,
            subject=handoff.summary,
            body=json.dumps({"handoff": handoff_row, "revision_request": payload}, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=target,
            references=(f"handoff:{handoff_row['handoff_id']}", f"request:{request_id}"),
            topic="integration_revision_handoff",
        )
        enqueue_work(target, str(task["project_id"]), "revision_request", request_id, task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        return RevisionRequest(
            request_id=request_id,
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            owner_role=target,
            subject=subject,
            reason=reason,
            mismatch_id=str(mismatch_data["mismatch_id"]) if mismatch_data.get("mismatch_id") else None,
            requested_changes=changes,
            evidence=refs,
            handoff_id=str(handoff_row["handoff_id"]),
            message_id=str(message["message_id"]),
        )

    def validate_contracts(
        self,
        task_id: str,
        frontend_contract: Mapping[str, object],
        backend_contract: Mapping[str, object],
        *,
        service_contracts: Iterable[Mapping[str, object]] = (),
        configuration: Iterable[Mapping[str, object]] = (),
        integration_tests: Iterable[object] = (),
        evidence: Iterable[object] = (),
        owner_role: str | None = None,
        run_id: str | None = None,
    ) -> IntegrationReport:
        """Compare boundary contracts and route any mismatch to the responsible owner."""
        task = self._task(task_id)
        refs = _items(evidence, max_chars=512)
        mismatches: list[ContractMismatch] = []
        for field in ("method", "path", "request_schema", "response_schema", "status_codes", "schema", "fields"):
            expected = _contract_value(frontend_contract, field)
            actual = _contract_value(backend_contract, field)
            if expected is None or actual is None or _canonical(expected) == _canonical(actual):
                continue
            mismatch = ContractMismatch(
                mismatch_id=str(uuid4()),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                boundary="frontend-backend-api",
                field=field,
                expected=expected,
                actual=actual,
                owner_role=_owner_role(owner_role or "backend"),
                evidence=refs,
            )
            message = self._publish(
                message_type=MessageType.BLOCKER,
                subject=f"API contract mismatch: {field}",
                body=json.dumps(mismatch.as_dict(), ensure_ascii=False),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                recipient_role=mismatch.owner_role,
                references=refs + (f"mismatch:{mismatch.mismatch_id}",),
                topic="integration_contract_mismatch",
            )
            mismatches.append(ContractMismatch(**{**asdict(mismatch), "message_id": str(message["message_id"])}))
        for contract in service_contracts:
            if not isinstance(contract, Mapping) or contract.get("compatible", True) is not False:
                continue
            mismatch = ContractMismatch(
                mismatch_id=str(uuid4()),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                boundary=_clean(contract.get("boundary") or "service-contract", max_chars=300),
                field=_clean(contract.get("field") or "service_contract", max_chars=300),
                expected=contract.get("expected"),
                actual=contract.get("actual"),
                owner_role=_owner_role(owner_role or contract.get("owner_role") or "backend"),
                evidence=refs + _items(contract.get("evidence") or (), max_chars=512),
            )
            message = self._publish(
                message_type=MessageType.BLOCKER,
                subject=f"Service contract mismatch: {mismatch.boundary}",
                body=json.dumps(mismatch.as_dict(), ensure_ascii=False),
                project_id=str(task["project_id"]),
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                recipient_role=mismatch.owner_role,
                references=refs + (f"mismatch:{mismatch.mismatch_id}",),
                topic="integration_contract_mismatch",
            )
            mismatches.append(ContractMismatch(**{**asdict(mismatch), "message_id": str(message["message_id"])}))
        failures: list[IntegrationFailure] = []
        for item in configuration:
            if isinstance(item, Mapping) and item.get("compatible", True) is False:
                failure = self.record_failure(
                    task_id,
                    boundary=str(item.get("boundary") or "configuration"),
                    reason=str(item.get("reason") or "Configuration compatibility check failed"),
                    owner_role=str(item.get("owner_role") or "configuration"),
                    evidence=refs + _items(item.get("evidence") or (), max_chars=512),
                    tests=(),
                    run_id=run_id,
                    create_revision=False,
                )
                failures.append(failure)
        tests = _items(integration_tests, max_chars=1000)
        for test in integration_tests or ():
            failed = isinstance(test, Mapping) and test.get("passed") is False
            if isinstance(test, str):
                failed = test.strip().casefold().startswith(("fail", "error")) or " failed" in test.casefold()
            if failed:
                failure = self.record_failure(
                    task_id,
                    boundary="integration-test",
                    reason=str(test.get("reason") if isinstance(test, Mapping) else test),
                    owner_role=owner_role,
                    evidence=refs,
                    tests=(str(test.get("name") if isinstance(test, Mapping) else test),),
                    run_id=run_id,
                    create_revision=False,
                )
                failures.append(failure)
        revision_ids: list[str] = []
        for mismatch in mismatches:
            revision_ids.append(self.request_revision(task_id, mismatch, mismatch.owner_role, evidence=refs, run_id=run_id).request_id)
        status = "passed" if not mismatches and not failures else "failed"
        payload = {
            "report_id": str(uuid4()),
            "status": status,
            "contract_mismatches": [item.as_dict() for item in mismatches],
            "failures": [item.as_dict() for item in failures],
            "checks": ["frontend_backend_contract", "service_contracts", "configuration_compatibility"],
            "tests": list(tests),
            "evidence": list(refs),
            "revision_request_ids": revision_ids,
        }
        message = self._publish(
            message_type=MessageType.RESULT,
            subject=f"Integration report: {task.get('title', task_id)}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=refs,
            topic="integration_report",
        )
        return IntegrationReport(
            report_id=payload["report_id"],
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            status=status,
            contract_mismatches=tuple(mismatches),
            failures=tuple(failures),
            checks=tuple(payload["checks"]),
            tests=tests,
            evidence=refs,
            revision_request_ids=tuple(revision_ids),
            message_id=str(message["message_id"]),
        )

    validate = validate_contracts
    verify = validate_contracts

    def record_success(
        self,
        task_id: str,
        *,
        checks: Iterable[object] = (),
        tests: Iterable[object] = (),
        evidence: Iterable[object] = (),
        run_id: str | None = None,
    ) -> IntegrationSuccess:
        task = self._task(task_id)
        check_items = _items(checks)
        test_items = _items(tests)
        evidence_items = _items(evidence, max_chars=512)
        if not check_items or (not test_items and not evidence_items):
            raise ValueError("integration success requires checks and test or evidence results")
        payload = {
            "success_id": str(uuid4()),
            "checks": list(check_items),
            "tests": list(test_items),
            "evidence": list(evidence_items),
            "status": "passed",
        }
        message = self._publish(
            message_type=MessageType.RESULT,
            subject=f"Integration success: {task.get('title', task_id)}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            references=evidence_items,
            topic="integration_success",
        )
        return IntegrationSuccess(payload["success_id"], str(task["project_id"]), str(task["id"]), check_items, test_items, evidence_items, "passed", str(message["message_id"]))

    def record_failure(
        self,
        task_id: str,
        *,
        boundary: str,
        reason: str,
        owner_role: str | None = None,
        evidence: Iterable[object] = (),
        tests: Iterable[object] = (),
        run_id: str | None = None,
        create_revision: bool = True,
    ) -> IntegrationFailure:
        task = self._task(task_id)
        clean_boundary = _clean(boundary, max_chars=300)
        clean_reason = _clean(reason, max_chars=6000)
        if not clean_boundary or not clean_reason:
            raise ValueError("integration failure requires a boundary and reason")
        target = _owner_role(owner_role) if owner_role else None
        refs = _items(evidence, max_chars=512)
        test_items = _items(tests, max_chars=1000)
        payload = {
            "failure_id": str(uuid4()),
            "boundary": clean_boundary,
            "reason": clean_reason,
            "owner_role": target,
            "evidence": list(refs),
            "tests": list(test_items),
        }
        message = self._publish(
            message_type=MessageType.BLOCKER,
            subject=f"Integration failure: {clean_boundary}",
            body=json.dumps(payload, ensure_ascii=False),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=target,
            references=refs,
            topic="integration_failure",
        )
        failure = IntegrationFailure(payload["failure_id"], str(task["project_id"]), str(task["id"]), clean_boundary, clean_reason, target, refs, test_items, "open", str(message["message_id"]))
        if create_revision and target:
            self.request_revision(task_id, failure.as_dict(), target, evidence=refs, run_id=run_id)
        return failure

    fail = record_failure


IntegrationEngineer = IntegrationEngineerAgent


__all__ = [
    "ContractMismatch",
    "IntegrationEngineer",
    "IntegrationEngineerAgent",
    "IntegrationFailure",
    "IntegrationReport",
    "IntegrationSuccess",
    "RevisionRequest",
]
