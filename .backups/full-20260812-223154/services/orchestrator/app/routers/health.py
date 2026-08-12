import asyncio
from typing import Any

import httpx
from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


async def probe(name: str, url: str) -> dict[str, Any]:
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
        }
    except Exception as exc:
        return {
            "name": name,
            "url": url,
            "ok": False,
            "error": str(exc),
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
        "version": "0.1.0",
        "dependencies": {
            "model_gateway": gateway,
            "local_agent": agent,
        },
    }