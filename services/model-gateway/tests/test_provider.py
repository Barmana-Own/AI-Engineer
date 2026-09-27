from __future__ import annotations

import httpx
import pytest

from app.exceptions import (
    ProviderAuthenticationError,
    ProviderModelUnavailableError,
    ProviderTimeoutError,
)
from app.providers.barmana import BarmanaProvider
from app.schemas import ChatMessage


@pytest.mark.asyncio
async def test_provider_uses_bearer_authentication(test_settings):
    captured_authorization = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_authorization
        captured_authorization = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {
                        "id": "auto",
                        "object": "model",
                        "owned_by": "barmana-ai",
                        "providers": ["automatic"],
                        "display_name": "Automatic",
                        "modality": "chat",
                    }
                ],
            },
        )

    async with httpx.AsyncClient(
        base_url=test_settings.normalized_base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = BarmanaProvider(test_settings, client=client)
        result = await provider.list_models()

    assert captured_authorization == "Bearer test-key"
    assert result.data[0].id == "auto"


@pytest.mark.asyncio
async def test_chat_request_contract(test_settings):
    captured_json = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_json
        captured_json = __import__("json").loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "id": "chat-1",
                "object": "chat.completion",
                "model": "auto",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "OK"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 1,
                    "total_tokens": 6,
                },
            },
        )

    async with httpx.AsyncClient(
        base_url=test_settings.normalized_base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = BarmanaProvider(test_settings, client=client)
        result = await provider.chat_completion(
            model="auto",
            messages=[ChatMessage(role="user", content="Reply OK")],
            temperature=0,
            max_tokens=8,
        )

    assert captured_json["model"] == "auto"
    assert captured_json["messages"][0]["role"] == "user"
    assert captured_json["stream"] is False
    assert result.choices[0].message["content"] == "OK"


@pytest.mark.asyncio
async def test_provider_maps_unauthorized_response(test_settings):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    async with httpx.AsyncClient(
        base_url=test_settings.normalized_base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = BarmanaProvider(test_settings, client=client)

        with pytest.raises(ProviderAuthenticationError):
            await provider.list_models()


@pytest.mark.asyncio
async def test_provider_maps_upstream_timeout(test_settings):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            504,
            json={"error": {"type": "upstream_timeout"}},
        )

    async with httpx.AsyncClient(
        base_url=test_settings.normalized_base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = BarmanaProvider(test_settings, client=client)

        with pytest.raises(ProviderTimeoutError):
            await provider.chat_completion(
                model="auto",
                messages=[ChatMessage(role="user", content="Hello")],
                temperature=0,
                max_tokens=8,
            )



@pytest.mark.asyncio
async def test_provider_maps_no_such_model_to_retryable_error(test_settings):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "type": "invalid_request",
                    "message": "AiError: No such model: missing-model",
                    "provider": "cloudflare",
                }
            },
        )

    async with httpx.AsyncClient(
        base_url=test_settings.normalized_base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = BarmanaProvider(test_settings, client=client)

        with pytest.raises(ProviderModelUnavailableError):
            await provider.chat_completion(
                model="auto",
                messages=[ChatMessage(role="user", content="Hello")],
                temperature=0,
                max_tokens=8,
            )


@pytest.mark.asyncio
async def test_native_ollama_chat_contract(test_settings):
    captured_path = None
    captured_json = None
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_path, captured_json
        captured_path = request.url.path
        captured_json = __import__("json").loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:8b",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "finish_task",
                                "arguments": {"status": "success"},
                            }
                        }
                    ],
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 5,
                "eval_count": 3,
            },
        )
    settings = test_settings.model_copy(
        update={"barmana_base_url": "http://127.0.0.1:11434/v1"}
    )
    async with httpx.AsyncClient(
        base_url=settings.normalized_base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = BarmanaProvider(settings, client=client)
        result = await provider.chat_completion(
            model="qwen3:8b",
            messages=[ChatMessage(role="user", content="Reply with a tool call")],
            temperature=0,
            max_tokens=8,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "finish_task",
                        "parameters": {"type": "object"},
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "finish_task"}},
            response_format={"type": "json_object"},
        )
    assert captured_path == "/api/chat"
    assert captured_json["think"] is False
    assert captured_json["stream"] is False
    assert captured_json["options"] == {"temperature": 0, "num_predict": 8}
    assert captured_json["tools"][0]["function"]["name"] == "finish_task"
    assert "tool_choice" not in captured_json
    assert captured_json["format"] == "json"
    assert result.model == "qwen3:8b"
    assert result.choices[0].message["tool_calls"][0]["function"]["name"] == "finish_task"
    assert result.usage.total_tokens == 8
