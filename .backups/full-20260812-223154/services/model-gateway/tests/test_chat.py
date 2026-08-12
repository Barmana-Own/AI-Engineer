from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import (
    ProviderChatChoice,
    ProviderChatResponse,
    ProviderUsage,
)


class SuccessfulProvider:
    name = "fake"

    async def list_models(self):
        raise AssertionError

    async def chat_completion(self, *, model, messages, temperature, max_tokens):
        return ProviderChatResponse(
            id="chat-1",
            object="chat.completion",
            model=model,
            choices=[
                ProviderChatChoice(
                    index=0,
                    message={"role": "assistant", "content": "OK"},
                    finish_reason="stop",
                )
            ],
            usage=ProviderUsage(
                prompt_tokens=5,
                completion_tokens=1,
                total_tokens=6,
            ),
        )

    async def close(self) -> None:
        return None


def test_chat_endpoint_and_usage_summary(test_settings):
    app = create_app(
        settings=test_settings,
        provider=SuccessfulProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": "Reply OK"}],
                "max_tokens": 8,
                "project_id": "project-1",
                "task_id": "task-1",
                "agent_id": "coding-agent",
            },
        )
        summary = client.get("/v1/usage/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "OK"
    assert body["gateway"]["selected_model"] == "auto"
    assert body["gateway"]["request_id"]

    assert summary.status_code == 200
    usage = summary.json()
    assert usage["total_requests"] == 1
    assert usage["successful_requests"] == 1
    assert usage["total_tokens"] == 6
