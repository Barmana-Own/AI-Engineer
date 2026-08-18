from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1, max_length=200)
    object: str | None = Field(default=None, max_length=64)
    created: int | None = None
    owned_by: str | None = Field(default=None, max_length=200)
    providers: list[Annotated[str, Field(max_length=100)]] = Field(default_factory=list, max_length=16)
    display_name: str | None = Field(default=None, max_length=200)
    modality: str | None = Field(default=None, max_length=64)


class ProviderModelList(BaseModel):
    model_config = ConfigDict(extra="allow")

    object: str = "list"
    data: list[ProviderModel] = Field(max_length=1000)


class GatewayModelList(BaseModel):
    object: str = "list"
    source: str = "barmana"
    cached: bool
    stale: bool
    fetched_at: datetime
    data: list[ProviderModel] = Field(max_length=1000)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1, max_length=100000)


class GatewayChatRequest(BaseModel):
    model: str | None = Field(default=None, max_length=200)
    fallback_models: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list,
        max_length=10,
    )
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=65536)
    stream: bool = False
    tools: list[dict[str, Any]] = Field(default_factory=list, max_length=64)
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

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ProviderChatChoice(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: int = Field(default=0, ge=0)
    message: dict[str, Any] | None = None
    text: str | None = Field(default=None, max_length=100000)
    finish_reason: str | None = Field(default=None, max_length=64)


class ProviderChatResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, max_length=200)
    object: str | None = Field(default=None, max_length=64)
    created: int | None = None
    model: str | None = Field(default=None, max_length=200)
    choices: list[ProviderChatChoice] = Field(default_factory=list, max_length=128)
    usage: ProviderUsage | None = None


class RoutingMetadata(BaseModel):
    provider: str = Field(max_length=100)
    requested_model: str | None = Field(default=None, max_length=200)
    selected_model: str = Field(max_length=200)
    attempted_models: list[Annotated[str, Field(max_length=200)]] = Field(max_length=16)
    fallback_used: bool
    latency_ms: int = Field(ge=0)
    request_id: str = Field(max_length=128)


class GatewayChatResponse(BaseModel):
    id: str | None = Field(default=None, max_length=200)
    object: str = Field(default="chat.completion", max_length=64)
    created: int | None = None
    model: str = Field(max_length=200)
    choices: list[ProviderChatChoice] = Field(max_length=128)
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

    provider: str = Field(max_length=100)
    provider_configured: bool
    default_model: str = Field(max_length=200)
    fallback_models: list[Annotated[str, Field(max_length=200)]] = Field(max_length=10)
    max_fallback_attempts: int = Field(ge=0)
    max_retries_per_model: int = Field(ge=0)
    fallback_on: list[Annotated[str, Field(max_length=64)]] = Field(max_length=16)
    candidate_order: str = Field(max_length=64)


class UsageModelSummary(BaseModel):
    model: str = Field(max_length=200)
    request_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    average_latency_ms: float = Field(ge=0)


class UsageSummary(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    by_model: list[UsageModelSummary]


class ErrorBody(BaseModel):
    code: str = Field(max_length=64)
    message: str = Field(max_length=1000)
    retryable: bool
    request_id: str | None = None
    details: dict[str, Any] | None = None
