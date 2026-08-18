"""Adapters for optional OpenAI-compatible provider endpoints.

The gateway keeps one hardened HTTP implementation in ``BarmanaProvider`` and
uses a small profile shim for additional providers. This supports OpenAI,
OpenRouter, Gemini's OpenAI-compatibility endpoint, Ollama and compatible
self-hosted gateways without copying provider SDKs or exposing credentials.
"""

from __future__ import annotations

from types import SimpleNamespace

from pydantic import SecretStr

from app.config import Settings
from app.providers.base import ProviderProfile
from app.providers.barmana import BarmanaProvider


class _ProfileSettings(SimpleNamespace):
    """Expose the Settings attributes consumed by the shared HTTP adapter."""

    def __init__(self, settings: Settings, profile: ProviderProfile) -> None:
        super().__init__(
            app_version=settings.app_version,
            barmana_base_url=profile.base_url,
            barmana_api_key=(SecretStr(profile.api_key) if profile.api_key else None),
            barmana_auth_mode=profile.auth_mode,
            barmana_models_path=profile.models_path,
            barmana_chat_path=profile.chat_path,
            connect_timeout_seconds=settings.connect_timeout_seconds,
            read_timeout_seconds=settings.read_timeout_seconds,
            write_timeout_seconds=settings.write_timeout_seconds,
            pool_timeout_seconds=settings.pool_timeout_seconds,
            max_provider_response_bytes=settings.max_provider_response_bytes,
            max_retries=settings.max_retries,
            retry_base_delay_seconds=settings.retry_base_delay_seconds,
        )

    @property
    def normalized_base_url(self) -> str:
        return str(self.barmana_base_url).rstrip("/")


class OpenAICompatibleProvider(BarmanaProvider):
    """Profiled provider using the shared OpenAI-compatible HTTP contract."""

    def __init__(
        self,
        settings: Settings,
        profile: ProviderProfile,
        *,
        client=None,
    ) -> None:
        self.profile = profile
        super().__init__(_ProfileSettings(settings, profile), client=client)
        self.name = profile.name

