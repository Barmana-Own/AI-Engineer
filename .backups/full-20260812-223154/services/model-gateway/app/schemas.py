from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    object: str | None = None
    created: int | None = None
    owned_by: str | None = None
    providers: list[str] = Field(default_factory=list)
    display_name: str | None = None
    modality: str | None = None


class ProviderModelList(BaseModel):
    model_config = ConfigDict(extra="allow")

    object: str = "list"
    data: list[ProviderModel]


class GatewayModelList(BaseModel):
    object: str = "list"
    source: str = "barmana"
    cached: bool
    stale: bool
    fetched_at: datetime
    data: list[ProviderModel]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1)


class GatewayChatRequest(BaseModel):
    model: str | None = None
    fallback_models: list[str] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None

    project_id: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)
    agent_id: str | None = Field(default=None, max_length=128)

    @field_validator("model")
    @classmethod
    def normalize_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("fallback_models")
    @classmethod
    def normalize_fallback_models(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            model = value.strip()
            if model and model not in seen:
                normalized.append(model)
                seen.add(model)

        return normalized

    @field_validator("stream")
    @classmethod
    def reject_streaming_for_mvp(cls, value: bool) -> bool:
        if value:
            raise ValueError("Streaming will be added in a later sub-step.")
        return value


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ProviderChatChoice(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: int = 0
    message: dict[str, Any] | None = None
    text: str | None = None
    finish_reason: str | None = None


class ProviderChatResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    object: str | None = None
    created: int | None = None
    model: str | None = None
    choices: list[ProviderChatChoice] = Field(default_factory=list)
    usage: ProviderUsage | None = None


class RoutingMetadata(BaseModel):
    provider: str
    requested_model: str | None
    selected_model: str
    attempted_models: list[str]
    fallback_used: bool
    latency_ms: int
    request_id: str


class GatewayChatResponse(BaseModel):
    id: str | None = None
    object: str = "chat.completion"
    created: int | None = None
    model: str
    choices: list[ProviderChatChoice]
    usage: ProviderUsage | None = None
    gateway: RoutingMetadata


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str
    provider: str
    provider_configured: bool


class ReadyResponse(BaseModel):
    status: Literal["ready"]
    provider: str
    model_count: int
    checked_at: datetime


class RuntimeModelsResponse(BaseModel):
    """Effective model/provider routing settings with secrets omitted."""

    provider: str
    provider_configured: bool
    default_model: str
    fallback_models: list[str]
    max_fallback_attempts: int
    max_retries_per_model: int
    fallback_on: list[str]
    candidate_order: str


class UsageModelSummary(BaseModel):
    model: str
    request_count: int
    success_count: int
    failure_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_latency_ms: float


class UsageSummary(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    by_model: list[UsageModelSummary]


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool
    request_id: str | None = None
    details: dict[str, Any] | None = None
