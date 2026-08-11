from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_model_router, get_usage_store
from app.exceptions import GatewayError
from app.router import ModelRouter
from app.schemas import (
    GatewayChatRequest,
    GatewayChatResponse,
    RoutingMetadata,
)
from app.usage import UsageRecord, UsageStore

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat/completions", response_model=GatewayChatResponse)
async def chat_completion(
    payload: GatewayChatRequest,
    request: Request,
    model_router: ModelRouter = Depends(get_model_router),
    usage_store: UsageStore = Depends(get_usage_store),
) -> GatewayChatResponse:
    started = perf_counter()
    request_id = request.state.request_id
    requested_model = payload.model
    attempted_models: list[str] = []
    selected_model: str | None = None

    try:
        result = await model_router.complete(payload)
        attempted_models = result.attempted_models
        selected_model = result.selected_model
        latency_ms = round((perf_counter() - started) * 1000)

        usage = result.response.usage
        prompt_tokens = usage.prompt_tokens if usage and usage.prompt_tokens else 0
        completion_tokens = (
            usage.completion_tokens if usage and usage.completion_tokens else 0
        )
        total_tokens = usage.total_tokens if usage and usage.total_tokens else 0

        await usage_store.record(
            UsageRecord(
                request_id=request_id,
                project_id=payload.project_id,
                task_id=payload.task_id,
                agent_id=payload.agent_id,
                requested_model=requested_model,
                selected_model=selected_model,
                attempted_models=attempted_models,
                status="success",
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                error_code=None,
            )
        )

        provider_response = result.response
        return GatewayChatResponse(
            id=provider_response.id,
            object=provider_response.object or "chat.completion",
            created=provider_response.created,
            model=provider_response.model or selected_model,
            choices=provider_response.choices,
            usage=provider_response.usage,
            gateway=RoutingMetadata(
                provider="barmana",
                requested_model=requested_model,
                selected_model=selected_model,
                attempted_models=attempted_models,
                fallback_used=len(attempted_models) > 1,
                latency_ms=latency_ms,
                request_id=request_id,
            ),
        )
    except GatewayError as exc:
        latency_ms = round((perf_counter() - started) * 1000)

        if exc.details and isinstance(exc.details.get("attempted_models"), list):
            attempted_models = [
                str(model) for model in exc.details["attempted_models"]
            ]

        await usage_store.record(
            UsageRecord(
                request_id=request_id,
                project_id=payload.project_id,
                task_id=payload.task_id,
                agent_id=payload.agent_id,
                requested_model=requested_model,
                selected_model=selected_model,
                attempted_models=attempted_models,
                status="failed",
                latency_ms=latency_ms,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                error_code=exc.code,
            )
        )
        raise
