from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakeProvider:
    name = "fake"

    async def list_models(self):
        raise AssertionError("Health endpoint must not call the provider.")

    async def chat_completion(self, **kwargs):
        raise AssertionError("Health endpoint must not call chat.")

    async def close(self) -> None:
        return None


def test_health_does_not_require_provider_connection(tmp_path):
    settings = Settings(
        app_environment="test",
        barmana_api_key=None,
        model_cache_path=tmp_path / "cache.json",
        usage_db_path=tmp_path / "usage.sqlite3",
    )
    app = create_app(settings=settings, provider=FakeProvider())

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["provider_configured"] is False
    assert response.headers["X-Request-ID"]
