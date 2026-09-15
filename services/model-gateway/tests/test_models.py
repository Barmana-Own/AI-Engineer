from __future__ import annotations

from fastapi.testclient import TestClient

from app.cache import ModelCatalogCache
from app.main import create_app
from app.schemas import ProviderModel, ProviderModelList


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def list_models(self) -> ProviderModelList:
        self.calls += 1
        return ProviderModelList(
            data=[
                ProviderModel(
                    id="codestral-latest",
                    object="model",
                    owned_by="barmana-ai",
                    providers=["mistral"],
                    modality="chat",
                )
            ]
        )

    async def chat_completion(self, **kwargs):
        raise AssertionError("Models endpoint must not call chat.")

    async def close(self) -> None:
        return None


def test_models_are_cached(test_settings):
    provider = FakeProvider()
    cache = ModelCatalogCache(
        path=test_settings.model_cache_path,
        ttl_seconds=300,
    )
    app = create_app(
        settings=test_settings,
        provider=provider,
        model_cache=cache,
    )

    with TestClient(app) as client:
        first = client.get("/v1/models")
        second = client.get("/v1/models")

    assert first.status_code == 200
    assert first.json()["cached"] is False
    assert first.json()["data"][0]["id"] == "codestral-latest"
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert provider.calls == 1


def test_refresh_bypasses_fresh_cache(test_settings):
    provider = FakeProvider()
    app = create_app(settings=test_settings, provider=provider)

    with TestClient(app) as client:
        assert client.get("/v1/models").status_code == 200
        assert client.get("/v1/models?refresh=true").status_code == 200

    assert provider.calls == 2
