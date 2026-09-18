from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=100_000)


class ChatTaskRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=32_768)
    project_id: str = Field(default="default", min_length=1, max_length=128)
    task_id: str = Field(default="chat-task", min_length=1, max_length=128)
    agent_id: str = Field(default="orchestrator", min_length=1, max_length=128)


class FileWriteTaskRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=1_048_576)
    overwrite: bool = False


class TerminalTaskRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    cwd: str = Field(default=".", max_length=500)
    shell: Literal["powershell", "cmd"] = "powershell"
    approved: bool = False
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)


class TerminalTaskResponse(BaseModel):
    preview: dict[str, Any]
    result: dict[str, Any]


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workspace: str | None = Field(default=None, max_length=240)


class ProjectResponse(BaseModel):
    id: str
    name: str
    workspace: str
    created_at: str
    updated_at: str


class AgentTaskCreateRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=3, max_length=8000)
    validation_command: str | None = Field(default=None, min_length=1, max_length=1000)
    mode: Literal["interactive", "autonomous"] = "interactive"


class AgentTaskResponse(BaseModel):
    id: str
    project_id: str
    instruction: str
    mode: Literal["interactive", "autonomous"]
    status: str
    plan: list[dict[str, Any]]
    current_step: int
    results: list[dict[str, Any]]
    approved_steps: list[int]
    pending: dict[str, Any] | None
    final_output: str | None
    error: str | None
    created_at: str
    updated_at: str
    run_id: str | None = None
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_expires_at: str | None = None
    heartbeat_at: str | None = None
    attempt_count: int = 0
    recovery_state: str = "new"
    failure_kind: str | None = None
    provider: str | None = None
    fallback_provider: str | None = None
    retry_after: str | None = None
    last_checkpoint_ref: str | None = None


class SelfImproveRequest(BaseModel):
    goal: str = Field(
        default="Inspect the project and complete the highest-value safe improvement.",
        min_length=10,
        max_length=2000,
    )
    cycles: int = Field(default=1, ge=1, le=5)


class AutonomyRunResponse(BaseModel):
    id: str
    project_id: str
    goal: str
    requested_cycles: int
    completed_cycles: int
    status: str
    task_ids: list[str]
    error: str | None
    created_at: str
    updated_at: str
    current_stage: str = "queued"
    recovery_state: str = "new"
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_expires_at: str | None = None
    heartbeat_at: str | None = None
    retry_count: int = 0
    failure_kind: str | None = None
    provider: str | None = None
    fallback_provider: str | None = None
    checkpoint_ref: str | None = None
    pending_approval: dict[str, Any] | None = None
    last_recovery_at: str | None = None


class SubagentHandoffResponse(BaseModel):
    id: str
    run_id: str
    project_id: str
    task_id: str | None
    role: str
    section: str
    schema_version: str
    status: str
    summary: str
    evidence: list[dict[str, Any]]
    changed_files: list[str]
    validations: list[dict[str, Any]]
    blockers: list[str]
    next_action: str | None
    confidence: float
    previous_handoff_ids: list[str]
    created_at: str
    updated_at: str


class MemoryResponse(BaseModel):
    id: str
    project_id: str
    task_id: str | None
    kind: str
    summary: str
    detail: dict[str, Any]
    confidence: float
    created_at: str
    use_count: int


class AgentApprovalRequest(BaseModel):
    approved: bool = True

class GitCheckpointRequest(BaseModel):
    message: str = Field(default="AI Engineer checkpoint", min_length=1, max_length=240)
    include_untracked: bool = True


class GitDiffRequest(BaseModel):
    staged: bool = False
    base: str | None = Field(default=None, max_length=80)


class GitRollbackRequest(BaseModel):
    commit: str = Field(min_length=4, max_length=80)
    approved: bool = False


class ManagedProcessStartRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    executable: str = Field(min_length=1, max_length=500)
    args: list[str] = Field(default_factory=list, max_length=100)
    cwd: str = Field(default=".", max_length=500)
    approved: bool = False


class ManagedProcessStopRequest(BaseModel):
    process_id: str = Field(min_length=1, max_length=100)
    approved: bool = False


class CoordinationRunRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=3, max_length=20_000)

class CoordinationMessageRequest(BaseModel):
    sender_role: str = Field(min_length=1, max_length=64)
    recipient_role: str | None = Field(default=None, max_length=64)
    message_type: str = Field(min_length=1, max_length=32)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=20_000)
    run_id: str | None = Field(default=None, max_length=120)
    project_id: str | None = Field(default=None, max_length=120)
    task_id: str | None = Field(default=None, max_length=120)
    references: list[str] = Field(default_factory=list, max_length=100)
    discussion_round: int = Field(default=0, ge=0, le=20)

class CoordinationHandoffRequest(BaseModel):
    sender_role: str = Field(min_length=1, max_length=64)
    recipient_role: str = Field(min_length=1, max_length=64)
    summary: str = Field(min_length=1, max_length=20_000)
    completed: list[str] = Field(default_factory=list, max_length=100)
    artifacts: list[str] = Field(default_factory=list, max_length=100)
    changed_files: list[str] = Field(default_factory=list, max_length=100)
    decisions: list[str] = Field(default_factory=list, max_length=100)
    risks: list[str] = Field(default_factory=list, max_length=100)
    remaining_work: list[str] = Field(default_factory=list, max_length=100)
    verification: list[str] = Field(default_factory=list, max_length=100)
    run_id: str | None = Field(default=None, max_length=120)
    project_id: str | None = Field(default=None, max_length=120)
    task_id: str | None = Field(default=None, max_length=120)

class CoordinationResultRequest(BaseModel):
    summary: str = Field(min_length=1, max_length=20_000)
    evidence: list[str] = Field(default_factory=list, max_length=100)
    approved: bool = True

class CoordinationFailureRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=20_000)

class CoordinationRevisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=20_000)


class ExperienceMemoryCreateRequest(BaseModel):
    project_id: str | None = Field(default=None, max_length=120)
    run_id: str | None = Field(default=None, max_length=120)
    task_id: str | None = Field(default=None, max_length=120)
    memory_type: Literal["working", "episodic", "project", "lesson", "failure"] = "episodic"
    lifecycle: Literal["candidate", "validated"] = "candidate"
    role: str | None = Field(default=None, max_length=128)
    task_type: str | None = Field(default=None, max_length=256)
    summary: str = Field(min_length=3, max_length=4_000)
    content: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class ExperiencePromotionRequest(BaseModel):
    target: Literal["validated", "trusted"] = "validated"
    evidence: list[dict[str, Any]] = Field(min_length=1, max_length=20)


class ExperienceOutcomeRequest(BaseModel):
    outcome: Literal["success", "failure", "review_rejected", "test_failed", "superseded"]
    task_success: bool | None = None
    tests_passed: bool | None = None
    review_accepted: bool | None = None
    rework_required: bool = False
    notes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)



class ImprovementObserveRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    repo_root: str | None = Field(default=None, max_length=500)


class ImprovementStartRequest(BaseModel):
    expected_files: list[str] = Field(default_factory=list, max_length=100)
    expected_tests: list[str] = Field(default_factory=list, max_length=100)


class ImprovementTestsRequest(BaseModel):
    tests_before: dict[str, Any] = Field(default_factory=dict)
    tests_after: dict[str, Any] = Field(default_factory=dict)
    regressions: list[str] = Field(default_factory=list, max_length=100)
    passed: bool | None = None


class ImprovementReviewRequest(BaseModel):
    tests_passed: bool = False
    review_accepted: bool = False
    acceptance_met: bool = False
    regressions: list[str] = Field(default_factory=list, max_length=100)
    notes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0, le=1)
    follow_up_tasks: list[str] = Field(default_factory=list, max_length=50)


class ImprovementInterruptRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


class ImprovementRollbackRequest(BaseModel):
    execute: bool = False


class RecoveryResumeRequest(BaseModel):
    verify: bool = False


class RecoveryLeaseRequest(BaseModel):
    owner_id: str | None = Field(default=None, max_length=200)
    run_id: str | None = Field(default=None, max_length=100)
    ttl_seconds: int = Field(default=600, ge=30, le=86400)


class RecoveryHeartbeatRequest(BaseModel):
    lease_token: str = Field(min_length=8, max_length=200)
    ttl_seconds: int = Field(default=600, ge=30, le=86400)


class RecoveryReleaseRequest(BaseModel):
    lease_token: str = Field(min_length=8, max_length=200)
    error: str | None = Field(default=None, max_length=2000)
