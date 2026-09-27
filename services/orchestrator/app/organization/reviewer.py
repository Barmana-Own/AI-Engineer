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


_REVIEW_TARGETS = frozenset({"backend", "frontend", "integration", "implementer", "architect", "debugger", "engineering_manager"})
_OUTCOMES = frozenset({"APPROVED", "APPROVED_WITH_NOTES", "REVISION_REQUIRED", "BLOCKED"})
_EVIDENCE_FIELDS = ("file", "diff", "test", "requirement", "decision")


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
class ReviewEvidence:
    file: str | None = None
    diff: str | None = None
    test: str | None = None
    requirement: str | None = None
    decision: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value}


@dataclass(frozen=True)
class ReviewFinding:
    finding_id: str
    summary: str
    severity: str
    recommendation: str
    evidence: tuple[ReviewEvidence, ...]
    status: str = "open"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


@dataclass(frozen=True)
class CodeReview:
    review_id: str
    project_id: str
    task_id: str
    outcome: str
    reviewer_role: str
    reviewed_role: str | None
    reviewed_agent: str | None
    findings: tuple[ReviewFinding, ...]
    evidence: tuple[ReviewEvidence, ...]
    status: str
    handoff_id: str | None = None
    message_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["findings"] = [item.as_dict() for item in self.findings]
        result["evidence"] = [item.as_dict() for item in self.evidence]
        return result


ReviewRecord = CodeReview


def _normalise_evidence(values: Iterable[object] | None) -> tuple[ReviewEvidence, ...]:
    result: list[ReviewEvidence] = []
    for raw in values or ():
        if isinstance(raw, ReviewEvidence):
            evidence = raw
        elif isinstance(raw, Mapping):
            fields = {key: _clean(raw.get(key), max_chars=2000) or None for key in _EVIDENCE_FIELDS}
            evidence = ReviewEvidence(**fields)
        else:
            text = _clean(raw, max_chars=2000)
            evidence = ReviewEvidence(test=text or None)
        if evidence.as_dict() and evidence not in result:
            result.append(evidence)
    return tuple(result[:100])


def _review_owner(task: Mapping[str, object], reviewed_role: str | None) -> str | None:
    candidate = reviewed_role
    if not candidate:
        inputs = task.get("inputs")
        if isinstance(inputs, Mapping):
            candidate = inputs.get("implementation_role") or inputs.get("owner_role") or inputs.get("author_role")
    if not candidate:
        return None
    role = _clean(candidate, max_chars=128).casefold()
    if role.startswith("employee-"):
        role = role.removeprefix("employee-")
    return role or None


def _target_role(value: str | None) -> str:
    role = _clean(value or "implementer", max_chars=128).casefold()
    if role.startswith("employee-"):
        role = role.removeprefix("employee-")
    if role not in _REVIEW_TARGETS:
        raise ValueError("review revisions must target a responsible engineering role")
    return role


class CodeReviewerAgent:
    """Independent, read-only reviewer that records evidence and routes revisions."""

    ROLE = "reviewer"
    DISPLAY_NAME = "Code Reviewer"
    AGENT_ID = "employee-reviewer"

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self.bus = MessageBus(self.database_path)
        self.handoffs = HandoffProtocol(self.database_path)

    def ensure_profile(self):
        return ensure_employee(
            self.ROLE,
            agent_id=self.AGENT_ID,
            display_name=self.DISPLAY_NAME,
            department=Department.QUALITY,
            status=EmployeeStatus.AVAILABLE,
            database_path=self.database_path,
        )

    def _task(self, task_id: str) -> dict[str, object]:
        task = coordination_store.get_task(str(task_id), database_path=self.database_path)
        if not task:
            raise KeyError(f"Review task not found: {task_id}")
        if str(task.get("role")) != self.ROLE:
            raise ValueError("Code Reviewer can only operate reviewer tasks")
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
        references: Iterable[str] = (),
        topic: str = "code_review",
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

    def _assert_independent(
        self,
        *,
        task: Mapping[str, object],
        reviewed_role: str | None,
        implementation_agent: str | None,
    ) -> str | None:
        owner = _review_owner(task, reviewed_role)
        agent = _clean(implementation_agent, max_chars=128) or None
        assigned = _clean(task.get("assigned_agent"), max_chars=128) or None
        if owner == self.ROLE or agent == self.AGENT_ID or assigned == self.AGENT_ID:
            raise PermissionError("Code Reviewer cannot review or approve its own implementation")
        return owner

    def _findings(self, findings: Iterable[object] | None, global_evidence: tuple[ReviewEvidence, ...]) -> tuple[ReviewFinding, ...]:
        result: list[ReviewFinding] = []
        for raw in findings or ():
            if isinstance(raw, Mapping):
                summary = _clean(raw.get("summary") or raw.get("finding") or raw.get("description"), max_chars=4000)
                severity = _clean(raw.get("severity") or "medium", max_chars=32).casefold()
                recommendation = _clean(raw.get("recommendation") or raw.get("requested_change") or "Address the finding and rerun review.", max_chars=4000)
                evidence = _normalise_evidence(raw.get("evidence") if isinstance(raw.get("evidence"), Iterable) and not isinstance(raw.get("evidence"), (str, bytes, Mapping)) else (raw.get("evidence"),) if raw.get("evidence") else ())
            else:
                summary = _clean(raw, max_chars=4000)
                severity = "medium"
                recommendation = "Address the finding and rerun review."
                evidence = ()
            if not summary:
                continue
            result.append(ReviewFinding(str(uuid4()), summary, severity or "medium", recommendation, evidence or global_evidence))
        return tuple(result[:100])

    def review_changes(
        self,
        task_id: str,
        *,
        outcome: str,
        findings: Iterable[object] = (),
        evidence: Iterable[object] = (),
        changed_files: Iterable[object] = (),
        diffs: Iterable[object] = (),
        tests: Iterable[object] = (),
        requirements: Iterable[object] = (),
        decisions: Iterable[object] = (),
        reviewed_role: str | None = None,
        implementation_agent: str | None = None,
        run_id: str | None = None,
    ) -> CodeReview:
        task = self._task(task_id)
        normalised_outcome = _clean(outcome, max_chars=64).upper().replace(" ", "_")
        if normalised_outcome not in _OUTCOMES:
            raise ValueError(f"unsupported review outcome: {outcome}")
        owner = self._assert_independent(task=task, reviewed_role=reviewed_role, implementation_agent=implementation_agent)
        all_evidence = list(_normalise_evidence(evidence))
        all_evidence.extend(ReviewEvidence(file=item) for item in _items(changed_files, max_chars=512))
        all_evidence.extend(ReviewEvidence(diff=item) for item in _items(diffs, max_chars=2000))
        all_evidence.extend(ReviewEvidence(test=item) for item in _items(tests, max_chars=1000))
        all_evidence.extend(ReviewEvidence(requirement=item) for item in _items(requirements, max_chars=1000))
        all_evidence.extend(ReviewEvidence(decision=item) for item in _items(decisions, max_chars=1000))
        unique_evidence = tuple(dict.fromkeys(item for item in all_evidence if item.as_dict()))[:100]
        if not unique_evidence:
            raise ValueError("review requires file, diff, test, requirement or decision evidence")
        review_findings = self._findings(findings, unique_evidence)
        if normalised_outcome in {"REVISION_REQUIRED", "BLOCKED"} and not review_findings:
            raise ValueError("revision or blocked review requires findings")
        review_id = str(uuid4())
        project_id = str(task["project_id"])
        message = self._publish(
            message_type=MessageType.REVIEW,
            subject=f"Code review: {task.get('title', task_id)}",
            body=json.dumps({"review_id": review_id, "outcome": normalised_outcome, "findings": [item.as_dict() for item in review_findings], "evidence": [item.as_dict() for item in unique_evidence]}, ensure_ascii=False),
            project_id=project_id,
            task_id=str(task["id"]),
            run_id=run_id or task.get("run_id"),
            recipient_role=owner,
            references=tuple(item.get("file") or item.get("test") or item.get("requirement") or item.get("decision") or item.get("diff") for item in (e.as_dict() for e in unique_evidence)),
            topic="code_review",
        )
        handoff_id: str | None = None
        if normalised_outcome in {"REVISION_REQUIRED", "BLOCKED"}:
            target = _target_role(owner)
            handoff = AgentHandoff(
                sender_role=self.ROLE,
                recipient_role=target,
                summary=f"Review revision required: {task.get('title', task_id)}",
                completed=("The change was independently reviewed.",),
                artifacts=("CodeReview", "ReviewFinding", "review_evidence"),
                changed_files=tuple(_items(changed_files, max_chars=512)),
                decisions=tuple(item.summary for item in review_findings),
                risks=("Technical completion is blocked until the responsible engineer responds.",),
                remaining_work=tuple(item.recommendation for item in review_findings),
                verification=tuple(item for e in unique_evidence for item in e.as_dict().values()),
                run_id=run_id or task.get("run_id"),
                project_id=project_id,
                task_id=str(task["id"]),
            )
            handoff_row = self.handoffs.submit(handoff)
            handoff_id = str(handoff_row["handoff_id"])
            self._publish(
                message_type=MessageType.REVISION_REQUEST,
                subject=handoff.summary,
                body=json.dumps({"review_id": review_id, "handoff": handoff_row, "findings": [item.as_dict() for item in review_findings]}, ensure_ascii=False),
                project_id=project_id,
                task_id=str(task["id"]),
                run_id=run_id or task.get("run_id"),
                recipient_role=target,
                references=(f"review:{review_id}", f"handoff:{handoff_id}"),
                topic="review_revision_request",
            )
            enqueue_work(target, project_id, "review_revision", review_id, task_id=str(task["id"]), priority=int(task.get("priority") or 50), database_path=self.database_path)
        return CodeReview(review_id, project_id, str(task["id"]), normalised_outcome, self.ROLE, owner, _clean(implementation_agent, max_chars=128) or None, review_findings, unique_evidence, normalised_outcome.casefold(), handoff_id, str(message["message_id"]))

    review = review_changes

    def request_revision(
        self,
        task_id: str,
        *,
        summary: str,
        evidence: Iterable[object],
        requested_changes: Iterable[object] = (),
        reviewed_role: str | None = None,
        implementation_agent: str | None = None,
        changed_files: Iterable[object] = (),
        run_id: str | None = None,
    ) -> CodeReview:
        recommendation = "; ".join(_items(requested_changes, max_chars=2000)) or "Repair the finding and rerun the review."
        finding = {"summary": summary, "severity": "high", "recommendation": recommendation, "evidence": evidence}
        return self.review_changes(task_id, outcome="REVISION_REQUIRED", findings=(finding,), evidence=evidence, changed_files=changed_files, reviewed_role=reviewed_role, implementation_agent=implementation_agent, run_id=run_id)

    def approve(
        self,
        task_id: str,
        *,
        evidence: Iterable[object],
        notes: Iterable[object] = (),
        reviewed_role: str | None = None,
        implementation_agent: str | None = None,
        run_id: str | None = None,
    ) -> CodeReview:
        findings = tuple({"summary": item, "severity": "note", "recommendation": "No revision required.", "evidence": evidence} for item in _items(notes))
        return self.review_changes(task_id, outcome="APPROVED_WITH_NOTES" if findings else "APPROVED", findings=findings, evidence=evidence, reviewed_role=reviewed_role, implementation_agent=implementation_agent, run_id=run_id)


ReviewerAgent = CodeReviewerAgent
CodeReviewer = CodeReviewerAgent
Reviewer = CodeReviewerAgent


__all__ = [
    "CodeReview",
    "CodeReviewer",
    "CodeReviewerAgent",
    "ReviewEvidence",
    "ReviewFinding",
    "ReviewRecord",
    "Reviewer",
    "ReviewerAgent",
]
