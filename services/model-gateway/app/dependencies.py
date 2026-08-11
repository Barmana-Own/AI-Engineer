from __future__ import annotations

from fastapi import Request

from app.cache import ModelCatalogCache
from app.config import Settings
from app.providers.base import ModelProvider
from app.router import ModelRouter
from app.usage import UsageStore


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_model_provider(request: Request) -> ModelProvider:
    return request.app.state.provider


def get_model_cache(request: Request) -> ModelCatalogCache:
    return request.app.state.model_cache


def get_model_router(request: Request) -> ModelRouter:
    return request.app.state.model_router


def get_usage_store(request: Request) -> UsageStore:
    return request.app.state.usage_store
