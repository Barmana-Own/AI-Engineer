from __future__ import annotations

import pytest

from app.exceptions import ProviderModelUnavailableError, ProviderTimeoutError
from app.router import ModelRouter
from app.schemas import (
    GatewayChatRequest,
    ProviderChatChoice,
    ProviderChatResponse,
)


class FallbackProvider:
    name = "fake"

    def __init__(self) -> None:
        self.models: list[str] = []

    async def list_models(self):
        raise AssertionError

    async def chat_completion(self, *, model, messages, temperature, max_tokens):
        self.models.append(model)

        if model == "auto":
            raise ProviderTimeoutError("timeout")

        return ProviderChatResponse(
            id="chat-1",
            object="chat.completion",
            model=model,
            choices=[
                ProviderChatChoice(
                    message={"role": "assistant", "content": "OK"}
                )
            ],
        )

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_router_uses_fallback_after_timeout(test_settings):
    provider = FallbackProvider()
    router = ModelRouter(test_settings, provider)

    result = await router.complete(
        GatewayChatRequest(
            model="auto",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=8,
        )
    )

    assert result.selected_model == "fallback-a"
    assert result.attempted_models == ["auto", "fallback-a"]
    assert provider.models == ["auto", "fallback-a"]



class MissingModelThenSuccessProvider:
    name = "fake"

    def __init__(self) -> None:
        self.models: list[str] = []

    async def list_models(self):
        raise AssertionError

    async def chat_completion(self, *, model, messages, temperature, max_tokens):
        self.models.append(model)

        if len(self.models) == 1:
            raise ProviderModelUnavailableError("No such model")

        return ProviderChatResponse(
            id="chat-2",
            object="chat.completion",
            model=model,
            choices=[
                ProviderChatChoice(
                    message={"role": "assistant", "content": "OK"}
                )
            ],
        )

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_router_falls_back_when_provider_model_is_missing(test_settings):
    provider = MissingModelThenSuccessProvider()
    router = ModelRouter(test_settings, provider)

    result = await router.complete(
        GatewayChatRequest(
            model="auto",
            fallback_models=["mistral-small-latest"],
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=8,
        )
    )

    assert result.selected_model == "mistral-small-latest"
    assert result.attempted_models == ["auto", "mistral-small-latest"]
