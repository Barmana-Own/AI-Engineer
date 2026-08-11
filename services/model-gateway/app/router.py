from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.exceptions import (
    GatewayError,
    NoModelSucceededError,
    ProviderRateLimitError,
    ProviderModelUnavailableError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.base import ModelProvider
from app.schemas import GatewayChatRequest, ProviderChatResponse


@dataclass(frozen=True)
class RoutingResult:
    response: ProviderChatResponse
    selected_model: str
    attempted_models: list[str]


class ModelRouter:
    """Selects a primary model and moves to fallbacks on retryable failures."""

    def __init__(self, settings: Settings, provider: ModelProvider) -> None:
        self._settings = settings
        self._provider = provider

    def build_candidates(self, request: GatewayChatRequest) -> list[str]:
        requested_model = request.model or self._settings.default_model

        raw_candidates = [
            requested_model,
            *request.fallback_models,
            *self._settings.parsed_fallback_models,
        ]

        candidates: list[str] = []
        seen: set[str] = set()

        for candidate in raw_candidates:
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                candidates.append(normalized)
                seen.add(normalized)

        return candidates[: self._settings.max_fallback_attempts]

    async def complete(self, request: GatewayChatRequest) -> RoutingResult:
        candidates = self.build_candidates(request)
        attempted: list[str] = []
        last_error: GatewayError | None = None
        max_tokens = min(
            request.max_tokens or self._settings.default_max_tokens,
            self._settings.hard_max_tokens,
        )

        for model in candidates:
            attempted.append(model)

            try:
                provider_arguments = {
                    "model": model,
                    "messages": request.messages,
                    "temperature": request.temperature,
                    "max_tokens": max_tokens,
                }
                if request.tools:
                    provider_arguments["tools"] = request.tools
                if request.tool_choice is not None:
                    provider_arguments["tool_choice"] = request.tool_choice
                if request.response_format is not None:
                    provider_arguments["response_format"] = request.response_format

                response = await self._provider.chat_completion(**provider_arguments)
                return RoutingResult(
                    response=response,
                    selected_model=model,
                    attempted_models=attempted,
                )
            except (
                ProviderTimeoutError,
                ProviderUnavailableError,
                ProviderRateLimitError,
                ProviderModelUnavailableError,
    ProviderModelUnavailableError,
            ) as exc:
                last_error = exc
                continue

        details: dict[str, object] = {"attempted_models": attempted}
        if last_error is not None:
            details["last_error_code"] = last_error.code
            details["last_error_details"] = last_error.details or {}

        raise NoModelSucceededError(
            "No configured model completed the request.",
            details=details,
        )
