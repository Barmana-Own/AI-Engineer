"""Independent release verification built on the existing coordination layer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping
from uuid import uuid4

from app.coordination import store as coordination_store
from app.coordination.bus import HandoffProtocol, MessageBus
from app.coordination.models import AgentHandoff, MessageType
from app.coordination.project_management import enqueue_work
from app.memory.sanitizer import sanitize_text

from .models import Department, EmployeeStatus
from .store import ensure_employee


_PASS_STATES = frozenset({"pass", "passed", "success", "succeeded", "complete", "completed", "ready", "accepted", "verified", "true"})
_FAIL_STATES = frozenset({"fail", "failed", "failure", "blocked", "rejected", "not_ready", "false", "error"})
_PENDING_STATES = frozenset({"pending", "waiting", "in_progress", "running", "open", "awaiting", "awaiting_review", "needs_review"})
_SEVERITIES = frozenset({"info", "low", "medium", "high", "critical"})
_ROUTE_BY_CATEGORY = {
    "requirements": "requirements",
    "acceptance_criteria": "requirements",
    "task_completion": "engineering_manager",
    "test_results": "tester",
    "integration_state": "integration",
    "review_state": "reviewer",
    "security_state": "security",
    "documentation_state": "docs",
    "deployment_readiness": "devops",
}
_ALLOWED_HANDOFFS = frozenset({
    "requirements",
    "engineering_manager",
    "tester",
    "integration",
    "reviewer",
    "security",
    "docs",
    "devops",
    "supervisor",
    "company_director",
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


@dataclass(frozen=True)
class VerificationEvidence:
    category: str
    description: str
    source: str | None = None
    status: str = "verified"

    def as_dict(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value}


@dataclass(frozen=True)
class ReleaseBlocker:
    blocker_id: str
    category: str
    reason: str
    evidence: tuple[VerificationEvidence, ...]
    responsible_role: str
    required_action: str
    severity: str = "high"
    status: str = "open"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


@dataclass(frozen=True)
class ReleaseVerification:
    verification_id: str
    project_id: str
    task_id: str
    result: str
    status: str
    evidence: tuple[VerificationEvidence, ...]
    blockers: tuple[ReleaseBlocker, ...]
    accepted_risks: tuple[str, ...] = ()
    message_id: str | None = None
    handoff_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = [item.as_dict() for item in self.evidence]
        result["blockers"] = [item.as_dict() for item in self.blockers]
        return result


def _state(value: object) -> str:
    if isinstance(value, bool):
        return "passed" if value else "failed"
    if isinstance(value, Mapping):
        if isinstance(value.get("passed"), bool):
            return "passed" if value["passed"] else "failed"
        raw = value.get("status") or value.get("state") or value.get("result") or value.get("outcome")
        return _clean(raw, max_chars=64).casefold().replace(" ", "_")
    return _clean(value, max_chars=64).casefold().replace(" ", "_")


def _raw_evidence(value: object) -> tuple[object, ...]:
    if isinstance(value, Mapping):
        for key in ("evidence", "proof", "verification", "tests", "items", "criteria", "artifacts"):
            if key in value and value[key] is not None:
                raw = value[key]
                if isinstance(raw, Mapping):
                    return tuple(raw.values())
                if isinstance(raw, (list, tuple, set, frozenset)):
                    return tuple(raw)
                return (raw,)
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(value)
    if value is None or isinstance(value, bool):
        return ()
    text = _clean(value, max_chars=4000)
    return (text,) if text else ()


def _normalise_evidence(category: str, value: object, explicit: Iterable[object] = ()) -> tuple[VerificationEvidence, ...]:
    raw_items = list(_raw_evidence(value)) + list(explicit)
    result: list[VerificationEvidence] = []
    for raw in raw_items:
        if isinstance(raw, VerificationEvidence):
            evidence = raw
        elif isinstance(raw, Mapping):
            description = _clean(raw.get("description") or raw.get("summary") or raw.get("evidence") or raw.get("name"), max_chars=4000)
            if not description:
                continue
            evidence = VerificationEvidence(
                category=category,
                description=description,
                source=_clean(raw.get("source") or raw.get("file") or raw.get("test") or raw.get("reference"), max_chars=1000) or None,
                status=_clean(raw.get("status") or "verified", max_chars=64) or "verified",
            )
        else:
            description = _clean(raw, max_chars=4000)
            if not description:
                continue
            evidence = VerificationEvidence(category, description)
        if evidence not in result:
            result.append(evidence)
        if len(result) >= 200:
            break
    return tuple(result)


def _risk_id(value: object) -> str:
    if isinstance(value, Mapping):
        return _clean(value.get("risk_id") or value.get("id") or value.get("title"), max_chars=256)
    return _clean(value, max_chars=256)


def _risk_is_accepted(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    state = _state(value)
    approver = _clean(value.get("approved_by") or value.get("owner") or value.get("decision_maker"), max_chars=256)
    evidence = _normalise_evidence("accepted_risk", value)
    return state in {"accepted", "approved", "verified"} and bool(approver and evidence)


class ReleaseVerifierAgent:
    """Independently verify release readiness; never implement missing work."""

    ROLE = "release_verifier"
    DISPLAY_NAME = "Release Verification Agent"
    AGENT_ID = "employee-release-verifier"

    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = database_path
        self.bus = MessageBus(database_path)
        self.handoffs = HandoffProtocol(database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id=self.AGENT_ID,
            display_name=self.DISPLAY_NAME,
            department=Department.OPERATIONS,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Release verification task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Release Verifier can only operate release_verifier tasks")
        return task

    def _publish(
        self,
        *,
        message_type: MessageType,
        subject: str,
        body: object,
        project_id: str,
        task_id: str,
        run_id: str | None,
        topic: str,
        recipient_role: str | None = None,
        references: Iterable[object] = (),
    ) -> dict[str, object]:
        payload = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, default=str)
        return self.bus.publish(
            sender_role=self.ROLE,
            message_type=message_type,
            subject=_clean(subject, max_chars=500),
            body=_clean(payload, max_chars=30_000),
            project_id=project_id,
            task_id=task_id,
            run_id=run_id,
            recipient_role=recipient_role,
            references=_items(references, max_chars=512),
            topic=topic,
        )

    def _blocker(
        self,
        *,
        category: str,
        reason: str,
        evidence: tuple[VerificationEvidence, ...],
        responsible_role: str | None,
        required_action: str,
        severity: str = "high",
    ) -> ReleaseBlocker:
        role = _clean(responsible_role or _ROUTE_BY_CATEGORY.get(category) or "supervisor", max_chars=128).casefold()
        if role not in _ALLOWED_HANDOFFS:
            role = _ROUTE_BY_CATEGORY.get(category, "supervisor")
        level = _clean(severity, max_chars=32).casefold()
        if level not in _SEVERITIES:
            level = "high"
        return ReleaseBlocker(
            blocker_id=str(uuid4()),
            category=category,
            reason=_clean(reason, max_chars=4000),
            evidence=evidence,
            responsible_role=role,
            required_action=_clean(required_action, max_chars=4000),
            severity=level,
        )

    def _evaluate_state(
        self,
        category: str,
        value: object,
        *,
        explicit_evidence: Iterable[object],
        responsible_role: str | None = None,
    ) -> tuple[tuple[VerificationEvidence, ...], tuple[ReleaseBlocker, ...]]:
        evidence = _normalise_evidence(category, value, explicit_evidence)
        state = _state(value)
        blockers: list[ReleaseBlocker] = []
        mapping = value if isinstance(value, Mapping) else {}
        missing = _items(mapping.get("missing") or mapping.get("unmet") or mapping.get("failed_criteria"), max_chars=2000)
        if not evidence:
            blockers.append(self._blocker(category=category, reason="Completion status was not supported by independent evidence.", evidence=evidence, responsible_role=responsible_role, required_action=f"Provide verified evidence for {category} and rerun release verification."))
        elif state in _FAIL_STATES:
            blockers.append(self._blocker(category=category, reason=f"Release evidence reports {state}.", evidence=evidence, responsible_role=responsible_role, required_action=f"Resolve the {category} failure and rerun its verification."))
        elif state in _PENDING_STATES or not state:
            blockers.append(self._blocker(category=category, reason=f"Release evidence for {category} is incomplete or pending.", evidence=evidence, responsible_role=responsible_role, required_action=f"Complete {category} and provide final evidence."))
        elif state not in _PASS_STATES:
            blockers.append(self._blocker(category=category, reason=f"Release evidence uses an unrecognized state: {state}.", evidence=evidence, responsible_role=responsible_role, required_action=f"Normalize {category} to a verified outcome and rerun release verification."))
        if missing:
            blockers.append(self._blocker(category=category, reason="Required criteria remain unmet.", evidence=evidence, responsible_role=responsible_role, required_action="Complete the missing criteria: " + "; ".join(missing)))
        return evidence, tuple(blockers)

    def _route_blocker(self, task: Mapping[str, object], blocker: ReleaseBlocker, run_id: str | None) -> str:
        handoff = AgentHandoff(
            sender_role=self.ROLE,
            recipient_role=blocker.responsible_role,
            summary=f"Release blocker: {blocker.category}",
            completed=("Independent release verification was performed.",),
            artifacts=("release_verification", "release_blocker"),
            risks=(blocker.reason,),
            remaining_work=(blocker.required_action,),
            verification=tuple(item.description for item in blocker.evidence),
            run_id=run_id or task.get("run_id"),
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
        )
        row = self.handoffs.submit(handoff)
        handoff_id = str(row["handoff_id"])
        self._publish(
            message_type=MessageType.HANDOFF,
            subject=handoff.summary,
            body={"handoff": row, "blocker": blocker.as_dict()},
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            topic="release_blocker_handoff",
            recipient_role=blocker.responsible_role,
            references=(f"handoff:{handoff_id}", f"blocker:{blocker.blocker_id}"),
        )
        enqueue_work(blocker.responsible_role, str(task["project_id"]), "release_blocker", blocker.blocker_id, task_id=str(task["id"]), priority=10, database_path=self.database_path)
        return handoff_id

    def verify_release(
        self,
        task_id: str,
        *,
        requirements: object,
        acceptance_criteria: object,
        task_completion: object,
        test_results: object,
        integration_state: object,
        review_state: object,
        security_state: object,
        documentation_state: object,
        deployment_readiness: object,
        accepted_risks: Iterable[object] = (),
        evidence: Mapping[str, Iterable[object]] | None = None,
        responsible_roles: Mapping[str, str] | None = None,
        run_id: str | None = None,
    ) -> ReleaseVerification:
        task = self._task(task_id)
        verification_id = str(uuid4())
        explicit = evidence or {}
        roles = responsible_roles or {}
        states = (
            ("requirements", requirements),
            ("acceptance_criteria", acceptance_criteria),
            ("task_completion", task_completion),
            ("test_results", test_results),
            ("integration_state", integration_state),
            ("review_state", review_state),
            ("security_state", security_state),
            ("documentation_state", documentation_state),
            ("deployment_readiness", deployment_readiness),
        )
        all_evidence: list[VerificationEvidence] = []
        blockers: list[ReleaseBlocker] = []
        for category, value in states:
            section_evidence, section_blockers = self._evaluate_state(
                category,
                value,
                explicit_evidence=explicit.get(category, ()),
                responsible_role=roles.get(category),
            )
            all_evidence.extend(section_evidence)
            blockers.extend(section_blockers)

        accepted: list[str] = []
        for raw_risk in accepted_risks:
            if _risk_is_accepted(raw_risk):
                risk_id = _risk_id(raw_risk)
                if risk_id and risk_id not in accepted:
                    accepted.append(risk_id)
        security_findings = security_state.get("findings") if isinstance(security_state, Mapping) else ()
        for finding in security_findings or ():
            if not isinstance(finding, Mapping):
                continue
            severity = _clean(finding.get("severity"), max_chars=32).casefold()
            status = _state(finding)
            if severity in {"high", "critical"} and status not in {"fixed", "resolved", "accepted", "approved", "verified"}:
                finding_id = _risk_id(finding)
                if finding_id not in accepted:
                    blockers.append(self._blocker(category="security_state", reason=f"Unresolved {severity} security finding blocks release.", evidence=_normalise_evidence("security_state", finding), responsible_role=roles.get("security") or "security", required_action="Fix the security finding and obtain an independent re-review.", severity=severity))
        if blockers:
            result = "NOT_READY"
        elif accepted:
            result = "READY_WITH_ACCEPTED_RISKS"
        else:
            result = "READY"
        status = result
        message_type = MessageType.RESULT if result != "NOT_READY" else MessageType.BLOCKER
        message = self._publish(
            message_type=message_type,
            subject=f"Release verification: {result}",
            body={"verification_id": verification_id, "result": result, "evidence": [item.as_dict() for item in all_evidence], "blockers": [item.as_dict() for item in blockers], "accepted_risks": accepted},
            project_id=str(task["project_id"]),
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            topic="release_verification",
            references=tuple(item.description for item in all_evidence),
        )
        handoffs = tuple(self._route_blocker(task, blocker, run_id) for blocker in blockers) if blockers else ()
        return ReleaseVerification(verification_id, str(task["project_id"]), str(task["id"]), result, status, tuple(all_evidence), tuple(blockers), tuple(accepted), str(message["message_id"]), handoffs)

    verify = verify_release
    check = verify_release


ReleaseVerifier = ReleaseVerifierAgent
ReleaseVerificationAgent = ReleaseVerifierAgent

__all__ = [
    "ReleaseBlocker",
    "ReleaseVerification",
    "ReleaseVerificationAgent",
    "ReleaseVerifier",
    "ReleaseVerifierAgent",
    "VerificationEvidence",
]



