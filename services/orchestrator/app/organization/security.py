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


_SEVERITIES = frozenset({"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"})
_OUTCOMES = frozenset({"APPROVED", "APPROVED_WITH_NOTES", "REVISION_REQUIRED", "BLOCKED", "ACCEPTED_RISK"})
_REVIEW_TARGETS = frozenset({
    "backend",
    "frontend",
    "integration",
    "implementer",
    "architect",
    "debugger",
    "engineering_manager",
    "operations",
})
_BLOCKING_SEVERITIES = frozenset({"HIGH", "CRITICAL"})
_EVIDENCE_FIELDS = ("file", "diff", "test", "requirement", "decision")


def _clean(value: object, *, max_chars: int = 4000) -> str:
    cleaned, _ = sanitize_text(str(value or ""), max_chars=max_chars)
    return cleaned.strip()


def _sequence(values: object | None) -> tuple[object, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Mapping)):
        return (values,)
    try:
        return tuple(values)  # type: ignore[arg-type]
    except TypeError:
        return (values,)


def _items(values: object | None, *, limit: int = 100, max_chars: int = 2000) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        item = _clean(value, max_chars=max_chars)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)


@dataclass(frozen=True)
class SecurityEvidence:
    file: str | None = None
    diff: str | None = None
    test: str | None = None
    requirement: str | None = None
    decision: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value}


@dataclass(frozen=True)
class SecurityFinding:
    finding_id: str
    title: str
    severity: str
    description: str
    remediation: str
    evidence: tuple[SecurityEvidence, ...]
    status: str = "open"
    blocks_release: bool = False

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


@dataclass(frozen=True)
class SecurityReview:
    review_id: str
    project_id: str
    task_id: str
    outcome: str
    reviewer_role: str
    reviewed_role: str | None
    findings: tuple[SecurityFinding, ...]
    evidence: tuple[SecurityEvidence, ...]
    status: str
    release_blocked: bool
    handoff_id: str | None = None
    message_id: str | None = None
    re_review_of: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["findings"] = [item.as_dict() for item in self.findings]
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


SecurityReviewRecord = SecurityReview


def _normalise_evidence(values: object | None) -> tuple[SecurityEvidence, ...]:
    result: list[SecurityEvidence] = []
    for raw in _sequence(values):
        if isinstance(raw, SecurityEvidence):
            evidence = raw
        elif isinstance(raw, Mapping):
            fields = {key: _clean(raw.get(key), max_chars=2000) or None for key in _EVIDENCE_FIELDS}
            evidence = SecurityEvidence(**fields)
        else:
            evidence = SecurityEvidence(test=_clean(raw, max_chars=2000) or None)
        if evidence.as_dict() and evidence not in result:
            result.append(evidence)
    return tuple(result[:100])


def _reviewed_role(task: Mapping[str, object], value: str | None) -> str | None:
    candidate: object | None = value
    if not candidate:
        inputs = task.get("inputs")
        if isinstance(inputs, Mapping):
            candidate = inputs.get("implementation_role") or inputs.get("owner_role") or inputs.get("author_role")
    if not candidate:
        return None
    role = _clean(candidate, max_chars=128).casefold()
    return role.removeprefix("employee-") or None


def _target_role(value: str | None) -> str:
    role = _clean(value or "engineering_manager", max_chars=128).casefold().removeprefix("employee-")
    if role not in _REVIEW_TARGETS:
        raise ValueError("security revisions must target a responsible engineering role")
    return role


class SecurityEngineerAgent:
    """Evidence-based, read-only security reviewer with explicit release gates."""

    ROLE = "security"
    DISPLAY_NAME = "Security Engineer"
    AGENT_ID = "employee-security"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id=self.AGENT_ID,
            display_name=self.DISPLAY_NAME,
            department=Department.SECURITY,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Security review task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Security Engineer can only operate security tasks")
        return task

    def _publish(
        self,
        *,
        message_type: MessageType,
        subject: str,
        body: str,
        project_id: str,
        task_id: str,
        run_id: str | None,
        recipient_role: str | None = None,
        references: object = (),
        topic: str = "security_review",
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

    def _findings(self, findings: object | None, evidence: tuple[SecurityEvidence, ...]) -> tuple[SecurityFinding, ...]:
        result: list[SecurityFinding] = []
        for raw in _sequence(findings):
            if isinstance(raw, Mapping):
                title = _clean(raw.get("title") or raw.get("summary") or raw.get("finding"), max_chars=500)
                description = _clean(raw.get("description") or raw.get("details") or title, max_chars=4000)
                remediation = _clean(raw.get("remediation") or raw.get("recommendation") or raw.get("requested_change"), max_chars=4000)
                severity = _clean(raw.get("severity") or "MEDIUM", max_chars=32).upper()
                local_evidence = _normalise_evidence(raw.get("evidence"))
            else:
                title = _clean(raw, max_chars=500)
                description = title
                remediation = "Address the finding and perform a security re-review."
                severity = "MEDIUM"
                local_evidence = ()
            if not title:
                continue
            if severity not in _SEVERITIES:
                raise ValueError(f"unsupported security severity: {severity}")
            blocks = severity in _BLOCKING_SEVERITIES
            result.append(
                SecurityFinding(
                    finding_id=str(uuid4()),
                    title=title,
                    severity=severity,
                    description=description,
                    remediation=remediation or "Address the finding and perform a security re-review.",
                    evidence=local_evidence or evidence,
                    blocks_release=blocks,
                )
            )
        return tuple(result[:100])

    def _assert_explicit_owner_policy(
        self,
        *,
        blocking_findings: tuple[SecurityFinding, ...],
        owner_approval: bool,
        authorization_reference: str | None,
    ) -> None:
        if blocking_findings and owner_approval and not _clean(authorization_reference, max_chars=512):
            raise PermissionError("high or critical risk acceptance requires an authorized policy decision reference")

    def review_changes(
        self,
        task_id: str,
        *,
        findings: object = (),
        evidence: object = (),
        changed_files: object = (),
        diffs: object = (),
        tests: object = (),
        requirements: object = (),
        decisions: object = (),
        reviewed_role: str | None = None,
        outcome: str | None = None,
        owner_approval: bool = False,
        authorization_reference: str | None = None,
        implementation_agent: str | None = None,
        re_review_of: str | None = None,
        run_id: str | None = None,
    ) -> SecurityReview:
        task = self._task(task_id)
        role = _reviewed_role(task, reviewed_role)
        if role == self.ROLE or _clean(implementation_agent, max_chars=128) == self.AGENT_ID or _clean(task.get("assigned_agent"), max_chars=128) == self.AGENT_ID:
            raise PermissionError("Security Engineer cannot review or approve its own implementation")
        all_evidence = list(_normalise_evidence(evidence))
        all_evidence.extend(SecurityEvidence(file=item) for item in _items(changed_files, max_chars=512))
        all_evidence.extend(SecurityEvidence(diff=item) for item in _items(diffs, max_chars=2000))
        all_evidence.extend(SecurityEvidence(test=item) for item in _items(tests, max_chars=1000))
        all_evidence.extend(SecurityEvidence(requirement=item) for item in _items(requirements, max_chars=1000))
        all_evidence.extend(SecurityEvidence(decision=item) for item in _items(decisions, max_chars=1000))
        unique_evidence = tuple(dict.fromkeys(item for item in all_evidence if item.as_dict()))[:100]
        if not unique_evidence:
            raise ValueError("security review requires file, diff, test, requirement or decision evidence")
        review_findings = self._findings(findings, unique_evidence)
        blocking = tuple(item for item in review_findings if item.blocks_release)
        self._assert_explicit_owner_policy(
            blocking_findings=blocking,
            owner_approval=owner_approval,
            authorization_reference=authorization_reference,
        )
        requested = _clean(outcome or ("BLOCKED" if blocking else "APPROVED"), max_chars=64).upper().replace(" ", "_")
        if requested not in _OUTCOMES:
            raise ValueError(f"unsupported security outcome: {outcome}")
        if blocking and requested in {"APPROVED", "APPROVED_WITH_NOTES"} and not owner_approval:
            requested = "BLOCKED"
        if blocking and requested == "ACCEPTED_RISK" and not owner_approval:
            requested = "BLOCKED"
        if requested in {"REVISION_REQUIRED", "BLOCKED"} and not review_findings:
            raise ValueError("blocked or revision-required security review needs findings")
        review_id = str(uuid4())
        project_id = str(task["project_id"])
        effective_run_id = run_id or task.get("run_id")
        message = self._publish(
            message_type=MessageType.REVIEW,
            subject=f"Security review: {task.get('title', task_id)}",
            body=json.dumps(
                {
                    "review_id": review_id,
                    "outcome": requested,
                    "release_blocked": bool(blocking and not owner_approval),
                    "findings": [item.as_dict() for item in review_findings],
                    "evidence": [item.as_dict() for item in unique_evidence],
                    "re_review_of": re_review_of,
                },
                ensure_ascii=False,
            ),
            project_id=project_id,
            task_id=str(task["id"]),
            run_id=effective_run_id,
            recipient_role=role,
            references=tuple(
                item.get("file") or item.get("test") or item.get("requirement") or item.get("decision") or item.get("diff")
                for item in (e.as_dict() for e in unique_evidence)
            ),
            topic="security_review",
        )
        handoff_id: str | None = None
        if requested in {"REVISION_REQUIRED", "BLOCKED"}:
            target = _target_role(role)
            handoff = AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target,
                summary=f"Security review requires action: {task.get('title', task_id)}",
                completed=("Security-sensitive changes were reviewed with concrete evidence.",),
                artifacts=("SecurityReview", "SecurityFinding", "security_evidence"),
                changed_files=tuple(_items(changed_files, max_chars=512)),
                decisions=tuple(item.title for item in review_findings),
                risks=tuple(f"{item.severity}: {item.title}" for item in review_findings),
                remaining_work=tuple(item.remediation for item in review_findings),
                verification=tuple(value for item in unique_evidence for value in item.as_dict().values()),
                run_id=effective_run_id,
                project_id=project_id,
                task_id=str(task["id"]),
            )
            handoff_row = self.handoffs.submit(handoff)
            handoff_id = str(handoff_row["handoff_id"])
            self._publish(
                message_type=MessageType.BLOCKER if requested == "BLOCKED" else MessageType.REVISION_REQUEST,
                subject=handoff.summary,
                body=json.dumps(
                    {
                        "review_id": review_id,
                        "handoff": handoff_row,
                        "findings": [item.as_dict() for item in review_findings],
                        "authorization_reference": authorization_reference,
                    },
                    ensure_ascii=False,
                ),
                project_id=project_id,
                task_id=str(task["id"]),
                run_id=effective_run_id,
                recipient_role=target,
                references=(f"security_review:{review_id}", f"handoff:{handoff_id}"),
                topic="security_blocker" if requested == "BLOCKED" else "security_revision_request",
            )
            enqueue_work(target, project_id, "security_revision", review_id, task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        if requested in {"BLOCKED", "ACCEPTED_RISK"} or blocking:
            self._publish(
                message_type=MessageType.DECISION,
                subject=f"Security decision escalation: {task.get('title', task_id)}",
                body=json.dumps(
                    {
                        "review_id": review_id,
                        "outcome": requested,
                        "blocking_severities": sorted({item.severity for item in blocking}),
                        "authorization_reference": authorization_reference,
                        "owner_approval": owner_approval,
                    },
                    ensure_ascii=False,
                ),
                project_id=project_id,
                task_id=str(task["id"]),
                run_id=effective_run_id,
                recipient_role="supervisor",
                references=(f"security_review:{review_id}",),
                topic="security_decision_escalation",
            )
        return SecurityReview(
            review_id=review_id,
            project_id=project_id,
            task_id=str(task["id"]),
            outcome=requested,
            reviewer_role=self.ROLE,
            reviewed_role=role,
            findings=review_findings,
            evidence=unique_evidence,
            status=requested.casefold(),
            release_blocked=bool(blocking and not owner_approval),
            handoff_id=handoff_id,
            message_id=str(message["message_id"]),
            re_review_of=re_review_of,
        )

    review = review_changes

    def re_review(
        self,
        task_id: str,
        *,
        previous_review_id: str,
        evidence: object,
        fixed_findings: object = (),
        reviewed_role: str | None = None,
        implementation_agent: str | None = None,
        run_id: str | None = None,
    ) -> SecurityReview:
        return self.review_changes(
            task_id,
            findings=fixed_findings,
            evidence=evidence,
            reviewed_role=reviewed_role,
            implementation_agent=implementation_agent,
            outcome="APPROVED" if not _sequence(fixed_findings) else "REVISION_REQUIRED",
            re_review_of=previous_review_id,
            run_id=run_id,
        )

    def escalate_decision(
        self,
        task_id: str,
        *,
        summary: str,
        evidence: object,
        severity: str = "HIGH",
        recipient_role: str = "supervisor",
        run_id: str | None = None,
    ) -> SecurityReview:
        finding = {
            "title": summary,
            "severity": severity,
            "description": summary,
            "remediation": "Obtain an authorized decision or remediate before release.",
            "evidence": evidence,
        }
        return self.review_changes(
            task_id,
            findings=(finding,),
            evidence=evidence,
            outcome="BLOCKED",
            reviewed_role=recipient_role if recipient_role in _REVIEW_TARGETS else "engineering_manager",
            run_id=run_id,
        )


SecurityAgent = SecurityEngineerAgent
SecurityReviewer = SecurityEngineerAgent


__all__ = [
    "SecurityAgent",
    "SecurityEngineerAgent",
    "SecurityEvidence",
    "SecurityFinding",
    "SecurityReview",
    "SecurityReviewRecord",
    "SecurityReviewer",
]
