from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import get_model_provider, get_runtime_settings
from app.providers.base import ModelProvider
from app.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_runtime_settings),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_environment,
        provider="barmana",
        provider_configured=settings.provider_configured,
    )


@router.get("/health/ready", response_model=ReadyResponse)
async def ready(
    provider: ModelProvider = Depends(get_model_provider),
) -> ReadyResponse:
    models = await provider.list_models()
    return ReadyResponse(
        status="ready",
        provider=provider.name,
        model_count=len(models.data),
        checked_at=datetime.now(UTC),
    )
