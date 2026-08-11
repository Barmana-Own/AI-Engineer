from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


class RuntimeProvider:
    name = "barmana"

    async def list_models(self):
        raise AssertionError("Runtime endpoint must not probe the provider catalog.")

    async def chat_completion(self, **kwargs):
        raise AssertionError("Runtime endpoint must not call chat.")

    async def close(self) -> None:
        return None


def test_runtime_models_reports_effective_routing_without_secrets(test_settings):
    app = create_app(settings=test_settings, provider=RuntimeProvider())

    with TestClient(app) as client:
        response = client.get("/v1/runtime/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "barmana"
    assert payload["provider_configured"] is True
    assert payload["default_model"] == "mistral-small-latest"
    assert payload["fallback_models"] == ["fallback-a", "fallback-b"]
    assert payload["max_fallback_attempts"] == 3
    assert "barmana_api_key" not in payload
    assert "requested model" in payload["candidate_order"]
