from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import ChatMessage, ProviderChatResponse, ProviderModelList


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
