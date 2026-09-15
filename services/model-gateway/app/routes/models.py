from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.cache import ModelCatalogCache
from app.dependencies import get_model_cache, get_model_provider
from app.exceptions import GatewayError
from app.providers.base import ModelProvider
from app.schemas import GatewayModelList

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models", response_model=GatewayModelList)
async def list_models(
    refresh: bool = Query(
        default=False,
        description="Ignore a fresh local cache and ask the provider again.",
    ),
    provider: ModelProvider = Depends(get_model_provider),
    cache: ModelCatalogCache = Depends(get_model_cache),
) -> GatewayModelList:
    if not refresh:
        cached = await cache.get_fresh()
        if cached is not None:
            return cached

    try:
        provider_models = await provider.list_models()
        return await cache.set(provider_models, source=provider.name)
    except GatewayError:
        stale = await cache.get_stale()
        if stale is not None:
            return stale
        raise
