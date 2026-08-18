from pathlib import Path

from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "AI Engineer Local Agent"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8011, ge=1, le=65535)
    workspace_root: str = "F:/AI-Engineer/workspaces"
    # The platform can supervise its own repository through a named alias.
    # The alias is resolved explicitly and never by accepting arbitrary
    # absolute paths from a client.
    self_workspace_name: str = "ai-engineer"
    self_workspace_root: str = "F:/AI-Engineer"

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
