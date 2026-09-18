import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    configured = os.getenv('AI_ENGINE_PROJECT_ROOT') or os.getenv('PROJECT_ROOT')
    if configured and configured.strip():
        return Path(configured).expanduser().resolve()
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (parent / 'services').is_dir() and (parent / 'apps').is_dir():
            return parent
    return current.parents[3]


class Settings(BaseSettings):
    app_name: str = "AI Engineer Orchestrator"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8012, ge=1, le=65535)

    model_gateway_url: str = Field(default="http://127.0.0.1:8010", min_length=1, max_length=500)
    local_agent_url: str = Field(default="http://127.0.0.1:8011", min_length=1, max_length=500)
    workspace_root: str = Field(
        default_factory=lambda: str(_project_root() / "workspaces"),
        min_length=1,
        max_length=500,
    )
    self_workspace_name: str = Field(default="ai-engineer", min_length=1, max_length=100)
    self_workspace_root: str = Field(
        default_factory=lambda: str(_project_root()),
        min_length=1,
        max_length=500,
    )

    request_timeout_seconds: int = Field(default=300, ge=1, le=3600)
    agent_model: str = Field(default="qwen2.5-coder:3b", min_length=1, max_length=200)
    autonomous_agent_model: str = Field(default="qwen2.5-coder:1.5b", min_length=1, max_length=200)

    # Opt-in background self-improvement. The API endpoint can always start a
    # bounded run explicitly; this switch lets the supervisor wake itself up.
    autonomous_mode_enabled: bool = False
    autonomous_interval_minutes: int = Field(default=5, ge=1, le=1440)
    autonomous_cycles_per_run: int = Field(default=1, ge=1, le=100)
    autonomous_workspace: str = Field(default="ai-engineer", min_length=1, max_length=200)
    autonomous_subagents: str = Field(default="scout,planner,implementer,verifier,reviewer", min_length=1, max_length=1000)
    autonomous_max_subagents: int = Field(default=5, ge=1, le=16)
    # Keep domain specialists opt-in so the default cycle spends its bounded
    # model budget on one writer and one validation reader.
    autonomous_include_section_specialist: bool = False
    # Read-only specialists may overlap on one immutable snapshot; writers remain serialized.
    autonomous_read_parallelism: int = Field(default=2, ge=1, le=8)
    autonomous_reconciliation_grace_seconds: int = Field(default=900, ge=0, le=86400)
    # Durable execution recovery is enabled by default; leases are renewed by workers.
    autonomous_recovery_enabled: bool = True
    autonomous_lease_seconds: int = Field(default=600, ge=30, le=86400)
    autonomous_recovery_stale_seconds: int = Field(default=900, ge=30, le=86400)
    autonomous_task_timeout_seconds: int = Field(default=360, ge=1, le=3600)
    autonomous_model_timeout_seconds: int = Field(default=180, ge=1, le=1800)
    # Push only clean, verified checkpoints to the configured GitHub remote.
    # The supervisor never publishes an uncommitted or foreign-repository tree.
    autonomous_auto_push: bool = False
    # Controlled self-improvement is opt-in and never pushes to remotes.
    autonomous_improvement_enabled: bool = False
    autonomous_max_changes_per_run: int = Field(default=1, ge=1, le=10)
    autonomous_max_retries: int = Field(default=2, ge=0, le=10)
    autonomous_max_runtime_seconds: int = Field(default=1800, ge=60, le=86400)
    autonomous_max_files_changed: int = Field(default=8, ge=1, le=100)
    autonomous_allowed_project_roots: str = Field(default="", max_length=2000)
    autonomous_allowed_commands: str = Field(default="", max_length=4000)
    autonomous_rollback_enabled: bool = False
    autonomous_repo_root: str = Field(
        default_factory=lambda: str(_project_root()),
        min_length=1,
        max_length=500,
    )
    autonomous_git_remote: str = Field(default="https://github.com/Barmana-Own/AI-Engineer.git", min_length=1, max_length=1000)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
