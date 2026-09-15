from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import get_model_provider, get_runtime_settings
from app.providers.base import ModelProvider
from app.schemas import RuntimeModelsResponse

router = APIRouter(prefix="/v1", tags=["runtime"])


@router.get("/runtime/models", response_model=RuntimeModelsResponse)
async def runtime_models(
    settings: Settings = Depends(get_runtime_settings),
    provider: ModelProvider = Depends(get_model_provider),
) -> RuntimeModelsResponse:
    """Expose the effective, non-secret model routing configuration.

    This endpoint deliberately reports configuration rather than probing the
    provider.  The provider's live catalog remains available from
    ``GET /v1/models``; this endpoint explains which model is selected first
    and the order used when the gateway falls back.
    """

    return RuntimeModelsResponse(
        provider=provider.name,
        provider_configured=settings.provider_configured,
        default_model=settings.default_model,
        fallback_models=list(settings.parsed_fallback_models),
        max_fallback_attempts=settings.max_fallback_attempts,
        max_retries_per_model=settings.max_retries,
        fallback_on=[
            "provider_timeout",
            "provider_unavailable",
            "provider_rate_limited",
            "provider_model_unavailable",
        ],
        candidate_order=(
            "requested model (or default_model) -> request fallback_models -> "
            "configured fallback_models"
        ),
    )
