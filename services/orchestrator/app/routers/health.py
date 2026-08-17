import asyncio
import time
from typing import Any

import httpx
from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


async def probe(name: str, url: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10),
            trust_env=False,
        ) as client:
            response = await client.get(url)

        return {
            "name": name,
            "url": url,
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        return {
            "name": name,
            "url": url,
            "ok": False,
            "error": str(exc),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }


@router.get("/health")
async def health() -> dict[str, Any]:
    gateway, agent = await asyncio.gather(
        probe(
            "model-gateway",
            f"{settings.model_gateway_url}/health",
        ),
        probe(
            "local-agent",
            f"{settings.local_agent_url}/health",
        ),
    )

    ready = bool(gateway["ok"] and agent["ok"])

    return {
        "status": "ok" if ready else "degraded",
        "service": settings.app_name,
        "version": "0.6.0",
        "dependencies": {
            "model_gateway": gateway,
            "local_agent": agent,
        },
    }
