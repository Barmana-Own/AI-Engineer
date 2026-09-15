from __future__ import annotations

import pytest

from app.providers.base import ModelProvider, ProviderProfile
from app.providers.pool import ProviderPool
from app.schemas import ChatMessage, ProviderChatResponse, ProviderModel, ProviderModelList


class FakeProvider(ModelProvider):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []

    async def list_models(self) -> ProviderModelList:
        return ProviderModelList(
            data=[ProviderModel(id="coder", providers=[self.name])]
        )

    async def chat_completion(self, *, model, messages, temperature, max_tokens, tools=None, tool_choice=None, response_format=None):
        self.calls.append(model)
        return ProviderChatResponse(
            id="chat-1",
            object="chat.completion",
            model=model,
            choices=[{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        )

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_pool_prefixes_catalog_and_routes_qualified_models():
    local = FakeProvider("barmana")
    cloud = FakeProvider("openrouter")
    pool = ProviderPool(
        {"barmana": local, "openrouter": cloud},
        (
            ProviderProfile("barmana", "http://local", default_model="local"),
            ProviderProfile("openrouter", "http://cloud", default_model="cloud"),
        ),
        default_name="barmana",
    )

    catalog = await pool.list_models()
    assert {model.id for model in catalog.data} == {"barmana/coder", "openrouter/coder"}

    response = await pool.chat_completion(
        model="openrouter/cloud",
        messages=[ChatMessage(role="user", content="hello")],
        temperature=0,
        max_tokens=8,
    )
    assert cloud.calls == ["cloud"]
    assert local.calls == []
    assert response.model == "openrouter/cloud"


def test_pool_exposes_profile_candidates():
    pool = ProviderPool(
        {"barmana": FakeProvider("barmana")},
        (ProviderProfile("barmana", "http://local", default_model="local", fallback_models=("backup",)),),
        default_name="barmana",
    )
    assert pool.candidate_models == ("barmana/local", "barmana/backup")
