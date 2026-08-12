from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from app.schemas import ChatMessage, ProviderChatResponse, ProviderModelList


@dataclass(frozen=True)
class ProviderProfile:
    """Secret-free runtime metadata for an OpenAI-compatible provider."""

    name: str
    base_url: str
    api_key: str | None = None
    auth_mode: Literal["bearer", "x-api-key", "api-key"] = "bearer"
    models_path: str = "/models"
    chat_path: str = "/chat/completions"
    default_model: str | None = None
    fallback_models: tuple[str, ...] = ()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())


class ModelProvider(ABC):
    name: str

    @abstractmethod
    async def list_models(self) -> ProviderModelList:
        raise NotImplementedError

    @abstractmethod
    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
    ) -> ProviderChatResponse:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
