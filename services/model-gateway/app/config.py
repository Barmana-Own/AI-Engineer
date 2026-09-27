from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.providers.base import ProviderProfile


def _project_root() -> Path:
    configured = os.getenv('AI_ENGINE_PROJECT_ROOT') or os.getenv('PROJECT_ROOT')
    if configured and configured.strip():
        return Path(configured).expanduser().resolve()
    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (parent / 'services').is_dir() and (parent / 'apps').is_dir():
            return parent
    return current.parents[3]


def _default_cache_path() -> Path:
    return _project_root() / "data" / "model-gateway" / "models-cache.json"


def _default_usage_db_path() -> Path:
    return _project_root() / "data" / "model-gateway" / "usage.sqlite3"


def _dotenv_secret(name: str) -> str | None:
    """Read one optional secret from the process or the local ignored .env."""
    value = os.getenv(name)
    if value:
        return value.strip().strip('"').strip("'") or None

    candidates = (Path.cwd() / ".env", _project_root() / "services" / "model-gateway" / ".env")
    for path in candidates:
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, raw = stripped.split("=", 1)
                if key.strip() != name:
                    continue
                secret = raw.strip().strip('"').strip("'")
                return secret or None
        except OSError:
            continue
    return None


def _normalize_profile_path(value: object, default: str) -> str:
    normalized = str(value or default).strip()
    if (not normalized.startswith("/") or normalized.startswith("//") or
            "://" in normalized or len(normalized) > 256):
        return default
    return normalized


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="AI Engineer Model Gateway", min_length=1, max_length=200)
    app_version: str = Field(default="0.2.1", min_length=1, max_length=64)
    app_environment: Literal["development", "test", "production"] = "development"

    gateway_host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    gateway_port: int = Field(default=8010, ge=1024, le=65535)
    gateway_log_level: str = Field(default="INFO", min_length=1, max_length=32)
    gateway_auth_required: bool = False
    gateway_auth_token: SecretStr | None = None

    barmana_base_url: AnyHttpUrl = "https://api.codemain.ir/v2/api"
    barmana_api_key: SecretStr | None = None
    barmana_auth_mode: Literal["bearer", "x-api-key", "api-key"] = "bearer"
    barmana_models_path: str = Field(default="/models", min_length=1, max_length=500)
    barmana_chat_path: str = Field(default="/chat/completions", min_length=1, max_length=500)

    # Optional provider profiles are supplied as JSON in the local .env file.
    # The value is never returned by an API endpoint and may contain secrets.
    # Example: {"openrouter":{"base_url":"https://openrouter.ai/api/v1",
    # "api_key":"...","default_model":"openai/gpt-4o-mini"}}
    provider_profiles_json: str = Field(default="", max_length=65536)

    # Optional local sidecar gateways (CLIProxyAPI, Codex Proxy, Codex2API,
    # or Sub2API).  Entries are disabled by default and only become active
    # when enabled and their local API key environment variable is present.
    local_bridge_profiles_json: str = Field(default="", max_length=65536)

    connect_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    read_timeout_seconds: float = Field(default=90.0, gt=0, le=600)
    write_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    pool_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    max_provider_response_bytes: int = Field(default=4 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024)

    # A retry is performed against the same model before moving to a fallback model.
    max_retries: int = Field(default=1, ge=0, le=5)
    retry_base_delay_seconds: float = Field(default=0.5, ge=0.1, le=10)

    model_cache_ttl_seconds: int = Field(default=300, ge=0, le=86400)
    model_cache_path: Path = Field(default_factory=_default_cache_path)
    usage_db_path: Path = Field(default_factory=_default_usage_db_path)

    default_model: str = Field(default="mistral-small-latest", max_length=200)
    fallback_models: str = Field(default="mistral-medium-latest,auto,codestral-latest", max_length=2048)
    max_fallback_attempts: int = Field(default=3, ge=1, le=10)

    default_max_tokens: int = Field(default=1024, ge=1, le=32768)
    hard_max_tokens: int = Field(default=8192, ge=1, le=65536)

    @field_validator("barmana_models_path", "barmana_chat_path")
    @classmethod
    def validate_api_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        if "://" in normalized:
            raise ValueError("API endpoint must be a relative path.")
        return normalized

    @field_validator("model_cache_path", "usage_db_path", mode="before")
    @classmethod
    def validate_storage_path(cls, value: object) -> object:
        if isinstance(value, (str, Path)):
            normalized = str(value).strip()
            if not normalized or len(normalized) > 500:
                raise ValueError("Storage path must be between 1 and 500 characters.")
        return value

    @field_validator("default_model")
    @classmethod
    def validate_default_model(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("default_model cannot be empty.")
        return normalized

    @property
    def provider_configured(self) -> bool:
        return bool(
            self.barmana_api_key
            and self.barmana_api_key.get_secret_value().strip()
        ) or any(profile.configured for profile in self.parsed_provider_profiles)

    @property
    def normalized_base_url(self) -> str:
        return str(self.barmana_base_url).rstrip("/")

    @property
    def parsed_fallback_models(self) -> tuple[str, ...]:
        return tuple(
            model.strip()
            for model in self.fallback_models.split(",")
            if model.strip()
        )

    @property
    def parsed_provider_profiles(self) -> tuple[ProviderProfile, ...]:
        """Parse optional provider profiles without failing local startup."""
        profiles: list[ProviderProfile] = []
        seen_names: set[str] = set()
        for raw in (self.provider_profiles_json, self.local_bridge_profiles_json):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue

            for name, value in payload.items():
                if len(profiles) >= 16:
                    break
                if not isinstance(value, dict) or value.get("enabled") is False:
                    continue
                normalized_name = str(name).strip().casefold()
                if not normalized_name or len(normalized_name) > 64 or normalized_name in seen_names:
                    continue
                base_url = str(value.get("base_url") or "").strip().rstrip("/")
                if (not base_url or len(base_url) > 500 or
                        not base_url.startswith(("http://", "https://"))):
                    continue
                auth_mode = str(value.get("auth_mode") or "bearer").strip().casefold()
                if auth_mode not in {"bearer", "x-api-key", "api-key"}:
                    auth_mode = "bearer"
                api_key = value.get("api_key")
                api_key_env = str(value.get("api_key_env") or "").strip()
                if not api_key and api_key_env:
                    api_key = _dotenv_secret(api_key_env)
                fallback = value.get("fallback_models") or ()
                if isinstance(fallback, str):
                    fallback = fallback.split(",")
                if isinstance(fallback, list) or isinstance(fallback, tuple):
                    normalized_fallback: list[str] = []
                    for item in fallback:
                        model = str(item).strip()
                        if model and len(model) <= 200 and model not in normalized_fallback:
                            normalized_fallback.append(model)
                        if len(normalized_fallback) >= 10:
                            break
                    fallback = tuple(normalized_fallback)
                else:
                    fallback = ()
                profiles.append(
                    ProviderProfile(
                        name=normalized_name,
                        base_url=base_url,
                        api_key=(str(api_key).strip() if api_key else None),
                        auth_mode=auth_mode,
                        models_path=_normalize_profile_path(value.get("models_path"), "/models"),
                        chat_path=_normalize_profile_path(value.get("chat_path"), "/chat/completions"),
                        default_model=(str(value.get("default_model")).strip() if value.get("default_model") else None),
                        fallback_models=fallback,
                    )
                )
                seen_names.add(normalized_name)
        return tuple(profiles)


@lru_cache
def get_settings() -> Settings:
    return Settings()
