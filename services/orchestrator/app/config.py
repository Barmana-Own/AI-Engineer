from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineer Orchestrator"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8012

    model_gateway_url: str = "http://127.0.0.1:8010"
    local_agent_url: str = "http://127.0.0.1:8011"

    request_timeout_seconds: int = 300
    agent_model: str = "qwen2.5-coder:3b"
    autonomous_agent_model: str = "qwen2.5-coder:1.5b"

    # Opt-in background self-improvement. The API endpoint can always start a
    # bounded run explicitly; this switch lets the supervisor wake itself up.
    autonomous_mode_enabled: bool = False
    autonomous_interval_minutes: int = 5
    autonomous_cycles_per_run: int = 1
    autonomous_workspace: str = "ai-engineer"
    autonomous_subagents: str = "scout,planner,implementer,verifier,reviewer"
    autonomous_max_subagents: int = 5
    autonomous_task_timeout_seconds: int = 360
    autonomous_model_timeout_seconds: int = 180

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
