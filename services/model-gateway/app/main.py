from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.cache import ModelCatalogCache
from app.config import Settings, get_settings
from app.exceptions import GatewayError
from app.providers.barmana import BarmanaProvider
from app.providers.base import ModelProvider
from app.router import ModelRouter
from app.routes import chat, health, models, runtime, usage
from app.schemas import ErrorBody
from app.usage import UsageStore

logger = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(
    *,
    settings: Settings | None = None,
    provider: ModelProvider | None = None,
    model_cache: ModelCatalogCache | None = None,
    model_router: ModelRouter | None = None,
    usage_store: UsageStore | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings.gateway_log_level)

    runtime_provider = provider or BarmanaProvider(runtime_settings)
    runtime_cache = model_cache or ModelCatalogCache(
        path=runtime_settings.model_cache_path,
        ttl_seconds=runtime_settings.model_cache_ttl_seconds,
    )
    runtime_router = model_router or ModelRouter(
        runtime_settings,
        runtime_provider,
    )
    runtime_usage_store = usage_store or UsageStore(
        runtime_settings.usage_db_path
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = runtime_settings
        application.state.provider = runtime_provider
        application.state.model_cache = runtime_cache
        application.state.model_router = runtime_router
        application.state.usage_store = runtime_usage_store

        await runtime_usage_store.initialize()
        logger.info("Model Gateway started on a local-only address.")

        try:
            yield
        finally:
            await runtime_provider.close()
            logger.info("Model Gateway stopped.")

    application = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.app_version,
        description=(
            "Local-first gateway between AI Engineer agents and model providers."
        ),
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(GatewayError)
    async def gateway_error_handler(
        request: Request,
        exc: GatewayError,
    ) -> JSONResponse:
        body = ErrorBody(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            request_id=getattr(request.state, "request_id", None),
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(mode="json"),
        )

    @application.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "service": runtime_settings.app_name,
            "version": runtime_settings.app_version,
            "health": "/health",
            "models": "/v1/models",
            "runtime_models": "/v1/runtime/models",
            "chat": "/v1/chat/completions",
            "usage": "/v1/usage/summary",
            "docs": "/docs",
        }

    application.include_router(health.router)
    application.include_router(models.router)
    application.include_router(runtime.router)
    application.include_router(chat.router)
    application.include_router(usage.router)
    return application


app = create_app()
