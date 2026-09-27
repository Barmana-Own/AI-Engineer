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
    assigned_role: str | None = Field(default=None, max_length=80)
    project_type: str = Field(default="", max_length=120)
    requirements: list[str] = Field(default_factory=list, max_length=40)
    risk: str = Field(default="", max_length=200)
    technologies: list[str] = Field(default_factory=list, max_length=40)
    project_phase: str = Field(default="", max_length=80)


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
    skill_selections: list[dict[str, Any]] = Field(default_factory=list)
    skill_trace: list[dict[str, Any]] = Field(default_factory=list)
    pending: dict[str, Any] | None
    final_output: str | None
    error: str | None
    created_at: str
    updated_at: str


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
