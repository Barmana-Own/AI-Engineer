from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    workspace_root: str


class FileEntry(BaseModel):
    name: str
    path: str
    type: str
    size: int | None = None


class FileListResponse(BaseModel):
    path: str
    entries: list[FileEntry]


class FileReadResponse(BaseModel):
    path: str
    content: str
    size: int


class FileWriteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=4 * 1024 * 1024)
    overwrite: bool = False


class FileWriteResponse(BaseModel):
    path: str
    size: int
    created: bool


TerminalShell = Literal["powershell", "cmd"]
TerminalRisk = Literal["safe", "approval_required", "blocked"]


class TerminalPreviewRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    cwd: str = Field(default=".", max_length=500)
    shell: TerminalShell = "powershell"


class TerminalPreviewResponse(BaseModel):
    command: str
    cwd: str
    shell: TerminalShell
    risk: TerminalRisk
    requires_approval: bool
    reasons: list[str]


class TerminalRunRequest(TerminalPreviewRequest):
    approved: bool = False
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)


class TerminalRunResponse(BaseModel):
    command: str
    cwd: str
    shell: TerminalShell
    risk: TerminalRisk
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int


class GitProjectRequest(BaseModel):
    project_path: str = Field(min_length=1, max_length=500)


class GitCheckpointRequest(GitProjectRequest):
    message: str = Field(default="AI Engineer checkpoint", min_length=1, max_length=240)
    include_untracked: bool = True


class GitDiffRequest(GitProjectRequest):
    staged: bool = False
    base: str | None = Field(default=None, max_length=80)


class GitRollbackRequest(GitProjectRequest):
    commit: str = Field(min_length=4, max_length=80)
    approved: bool = False


class ProcessStartRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    executable: str = Field(min_length=1, max_length=500)
    args: list[Annotated[str, Field(max_length=2048)]] = Field(
        default_factory=list,
        max_length=100,
    )
    cwd: str = Field(default=".", max_length=500)
    approved: bool = False


class ProcessStopRequest(BaseModel):
    process_id: str = Field(min_length=1, max_length=100)
    approved: bool = False


class ManagedProcessResponse(BaseModel):
    id: str
    name: str
    executable: str
    args: list[str]
    cwd: str
    pid: int
    running: bool
    started_at: str
    stdout_log: str
    stderr_log: str


class GenericResponse(BaseModel):
    ok: bool
    data: dict[str, Any]