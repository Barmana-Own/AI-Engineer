from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineer Orchestrator"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8012

    model_gateway_url: str = "http://127.0.0.1:8010"
    local_agent_url: str = "http://127.0.0.1:8011"

    request_timeout_seconds: int = 300
    agent_model: str = "qwen2.5-coder:1.5b"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
