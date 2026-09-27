from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import GatewayAuthMiddleware


def _gateway_fixture() -> FastAPI:
    application = FastAPI()
    application.add_middleware(
        GatewayAuthMiddleware,
        required=True,
        token="gateway-secret",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/v1/runtime/models")
    def runtime_models() -> dict[str, str]:
        return {"provider": "test"}

    return application


def test_gateway_health_is_public_but_model_routes_are_protected() -> None:
    client = TestClient(_gateway_fixture())
    assert client.get("/health").status_code == 200
    assert client.get("/v1/runtime/models").status_code == 401
    response = client.get(
        "/v1/runtime/models",
        headers={"X-AI-Engine-Token": "gateway-secret"},
    )
    assert response.status_code == 200
