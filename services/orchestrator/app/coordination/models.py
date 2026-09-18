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
    RESULT = "RESULT"
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
    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "purpose": self.purpose, "responsibilities": list(self.responsibilities), "capabilities": list(self.capabilities), "allowed_tools": list(self.allowed_tools), "write_permission": self.write_permission.value, "default_model_profile": self.default_model_profile, "input_expectations": list(self.input_expectations), "output_contract": list(self.output_contract), "escalation_rules": list(self.escalation_rules)}
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
    message_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str | None = None
    def as_dict(self) -> dict[str, object]:
        return {"message_id": self.message_id, "run_id": self.run_id, "project_id": self.project_id, "task_id": self.task_id, "sender_role": self.sender_role, "recipient_role": self.recipient_role, "message_type": self.message_type.value, "subject": self.subject, "body": self.body, "references": list(self.references), "discussion_round": self.discussion_round, "created_at": self.created_at}
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
    handoff_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "submitted"
    def as_dict(self) -> dict[str, object]:
        return {"handoff_id": self.handoff_id, "run_id": self.run_id, "project_id": self.project_id, "task_id": self.task_id, "sender_role": self.sender_role, "recipient_role": self.recipient_role, "summary": self.summary, "completed": list(self.completed), "artifacts": list(self.artifacts), "changed_files": list(self.changed_files), "decisions": list(self.decisions), "risks": list(self.risks), "remaining_work": list(self.remaining_work), "verification": list(self.verification), "status": self.status}
