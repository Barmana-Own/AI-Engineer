from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence
from uuid import uuid4
MAX_TEXT = 20000
MAX_LIST = 100
class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    ASSIGNED = "assigned"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    REVIEW = "review"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
class MessageType(str, Enum):
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    PROPOSAL = "PROPOSAL"
    EVIDENCE = "EVIDENCE"
    REVIEW = "REVIEW"
    CHALLENGE = "CHALLENGE"
    REVISION_REQUEST = "REVISION_REQUEST"
    DECISION = "DECISION"
    HANDOFF = "HANDOFF"
    BLOCKER = "BLOCKER"
    STATUS = "STATUS"
    COUNTER_PROPOSAL = "COUNTER_PROPOSAL"
    DISSENT = "DISSENT"
    RESULT = "RESULT"
class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    PROJECT = "project"
    DEPARTMENT = "department"


class MeetingType(str, Enum):
    PROJECT_KICKOFF = "PROJECT_KICKOFF"
    REQUIREMENTS_REVIEW = "REQUIREMENTS_REVIEW"
    ARCHITECTURE_REVIEW = "ARCHITECTURE_REVIEW"
    ENGINEERING_SYNC = "ENGINEERING_SYNC"
    BUG_TRIAGE = "BUG_TRIAGE"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    RELEASE_REVIEW = "RELEASE_REVIEW"
    POSTMORTEM = "POSTMORTEM"


class WorkRequestStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ANSWERED = "answered"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class WritePermission(str, Enum):
    READ_ONLY = "read_only"
    SCOPED = "scoped_write"
    WORKSPACE = "workspace_write"
def _text(value: object, limit: int = MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]
def _items(values: Sequence[object] | None, limit: int = MAX_LIST) -> tuple[str, ...]:
    result: list[str] = []
    for value in values or ():
        item = _text(value, 2000)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return tuple(result)
@dataclass(frozen=True)
class RoleContract:
    id: str
    name: str
    purpose: str
    responsibilities: tuple[str, ...]
    capabilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    write_permission: WritePermission
    default_model_profile: str
    input_expectations: tuple[str, ...]
    output_contract: tuple[str, ...]
    escalation_rules: tuple[str, ...]
    writable_scope: tuple[str, ...] = ()
    performance_signals: tuple[str, ...] = ()
    handoff_targets: tuple[str, ...] = ()
    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "purpose": self.purpose, "responsibilities": list(self.responsibilities), "capabilities": list(self.capabilities), "allowed_tools": list(self.allowed_tools), "write_permission": self.write_permission.value, "writable_scope": list(self.writable_scope), "default_model_profile": self.default_model_profile, "input_expectations": list(self.input_expectations), "output_contract": list(self.output_contract), "escalation_rules": list(self.escalation_rules), "performance_signals": list(self.performance_signals), "handoff_targets": list(self.handoff_targets)}
@dataclass
class CoordinationTask:
    project_id: str
    title: str
    description: str
    role: str
    run_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    parent_task_id: str | None = None
    assigned_agent: str | None = None
    state: TaskState = TaskState.PENDING
    priority: int = 50
    dependencies: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    inputs: Mapping[str, object] = field(default_factory=dict)
    expected_outputs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    retry_count: int = 0
    max_retries: int = 2
    failure_reason: str | None = None
    scope: tuple[str, ...] = ()
    writer: bool = False
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str | None = None
    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "project_id": self.project_id, "run_id": self.run_id, "parent_task_id": self.parent_task_id, "title": self.title, "description": self.description, "role": self.role, "assigned_agent": self.assigned_agent, "state": self.state.value, "priority": self.priority, "dependencies": list(self.dependencies), "blocked_by": list(self.blocked_by), "inputs": dict(self.inputs), "expected_outputs": list(self.expected_outputs), "acceptance_criteria": list(self.acceptance_criteria), "retry_count": self.retry_count, "max_retries": self.max_retries, "failure_reason": self.failure_reason, "scope": list(self.scope), "writer": self.writer, "created_at": self.created_at, "started_at": self.started_at, "completed_at": self.completed_at, "updated_at": self.updated_at}

@dataclass(frozen=True)
class AgentHandoff:
    sender_role: str
    recipient_role: str
    summary: str
    completed: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    remaining_work: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    run_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    status: str = "pending"
    handoff_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str | None = None
    updated_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "handoff_id": self.handoff_id,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "sender_role": self.sender_role,
            "recipient_role": self.recipient_role,
            "status": self.status,
            "summary": self.summary,
            "completed": list(self.completed),
            "artifacts": list(self.artifacts),
            "changed_files": list(self.changed_files),
            "decisions": list(self.decisions),
            "risks": list(self.risks),
            "remaining_work": list(self.remaining_work),
            "verification": list(self.verification),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class AgentMessage:
    sender_role: str
    message_type: MessageType
    subject: str
    body: str
    run_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    recipient_role: str | None = None
    references: tuple[str, ...] = ()
    discussion_round: int = 0
    conversation_id: str | None = None
    audience_type: str = ConversationType.DIRECT.value
    audience_id: str | None = None
    participant_roles: tuple[str, ...] = ()
    topic: str = ""
    message_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "message_id": self.message_id,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "sender_role": self.sender_role,
            "recipient_role": self.recipient_role,
            "message_type": self.message_type.value,
            "subject": self.subject,
            "body": self.body,
            "references": list(self.references),
            "discussion_round": self.discussion_round,
            "conversation_id": self.conversation_id,
            "audience_type": self.audience_type,
            "audience_id": self.audience_id,
            "participant_roles": list(self.participant_roles),
            "topic": self.topic,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TechnicalDecision:
    project_id: str
    title: str
    context: str
    decision: str
    decision_maker: str
    options: tuple[str, ...] = ()
    arguments: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    affected_tasks: tuple[str, ...] = ()
    run_id: str | None = None
    meeting_id: str | None = None
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    superseded_by: str | None = None
    created_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "meeting_id": self.meeting_id,
            "title": self.title,
            "context": self.context,
            "options": list(self.options),
            "arguments": list(self.arguments),
            "decision": self.decision,
            "decision_maker": self.decision_maker,
            "supporting_evidence": list(self.supporting_evidence),
            "affected_tasks": list(self.affected_tasks),
            "created_at": self.created_at,
            "superseded_by": self.superseded_by,
        }


@dataclass
class StructuredMeeting:
    project_id: str
    meeting_type: MeetingType | str
    objective: str
    participants: tuple[str, ...]
    agenda: tuple[str, ...] = ()
    run_id: str | None = None
    meeting_id: str = field(default_factory=lambda: str(uuid4()))
    message_ids: tuple[str, ...] = ()
    decision_ids: tuple[str, ...] = ()
    action_items: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    status: str = "scheduled"
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        meeting_type = (
            self.meeting_type.value
            if isinstance(self.meeting_type, MeetingType)
            else str(self.meeting_type)
        )
        return {
            "meeting_id": self.meeting_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "meeting_type": meeting_type,
            "objective": self.objective,
            "participants": list(self.participants),
            "agenda": list(self.agenda),
            "message_ids": list(self.message_ids),
            "decision_ids": list(self.decision_ids),
            "action_items": list(self.action_items),
            "unresolved_questions": list(self.unresolved_questions),
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class InternalWorkRequest:
    sender: str
    recipient: str
    project_id: str
    request_type: str
    description: str
    priority: int = 50
    run_id: str | None = None
    task_id: str | None = None
    status: WorkRequestStatus | str = WorkRequestStatus.OPEN
    response: str = ""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str | None = None
    updated_at: str | None = None
    resolved_at: str | None = None

    def as_dict(self) -> dict[str, object]:
        status = self.status.value if isinstance(self.status, WorkRequestStatus) else str(self.status)
        return {
            "request_id": self.request_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "request_type": self.request_type,
            "description": self.description,
            "priority": self.priority,
            "status": status,
            "response": self.response,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }
