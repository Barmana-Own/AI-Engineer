from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineer Local Agent"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8011
    workspace_root: str = "F:/AI-Engineer/workspaces"
    # The platform can supervise its own repository through a named alias.
    # The alias is resolved explicitly and never by accepting arbitrary
    # absolute paths from a client.
    self_workspace_name: str = "ai-engineer"
    self_workspace_root: str = "F:/AI-Engineer"

    command_timeout_seconds: int = 60
    max_command_timeout_seconds: int = 300
    max_command_length: int = 4000
    max_command_output_bytes: int = 262_144

    max_file_read_bytes: int = 1_048_576
    max_file_write_bytes: int = 1_048_576
    max_list_entries: int = 500

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
