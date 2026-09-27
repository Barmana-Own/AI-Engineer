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
    app_name: str = Field(default="AI Engineer Local Agent", min_length=1, max_length=200)
    environment: str = Field(default="development", min_length=1, max_length=32)
    host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    port: int = Field(default=8011, ge=1, le=65535)
    workspace_root: str = Field(
        default_factory=lambda: str(_project_root() / "workspaces"),
        min_length=1,
        max_length=500,
    )
    # The platform can supervise its own repository through a named alias.
    # The alias is resolved explicitly and never by accepting arbitrary
    # absolute paths from a client.
    self_workspace_name: str = Field(default="ai-engineer", min_length=1, max_length=100)
    self_workspace_root: str = Field(
        default_factory=lambda: str(_project_root()),
        min_length=1,
        max_length=500,
    )

    managed_process_registry_path: str = Field(
        default_factory=lambda: str(_project_root() / "data" / "local-agent" / "processes.json"),
        min_length=1,
        max_length=500,
    )
    managed_process_log_root: str = Field(
        default_factory=lambda: str(_project_root() / "logs" / "managed-processes"),
        min_length=1,
        max_length=500,
    )

    command_timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_command_timeout_seconds: int = Field(default=300, ge=1, le=3600)
    max_command_length: int = Field(default=4000, ge=1, le=100_000)
    max_command_output_bytes: int = Field(default=262_144, ge=1024, le=16 * 1024 * 1024)

    max_file_read_bytes: int = Field(default=1_048_576, ge=1, le=64 * 1024 * 1024)
    max_file_write_bytes: int = Field(default=1_048_576, ge=1, le=64 * 1024 * 1024)
    max_list_entries: int = Field(default=500, ge=1, le=10_000)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def workspace_path(self) -> Path:
        path = Path(self.workspace_root).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def self_workspace_path(self) -> Path:
        return Path(self.self_workspace_root).expanduser().resolve()


settings = Settings()
