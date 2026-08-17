from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import settings


async def request_json(
    method: str,
    url: str,
    *,
    json: dict[str, Any] | None = None,
    timeout_seconds: int | None = None,
) -> Any:
    effective_timeout = max(float(timeout_seconds or settings.request_timeout_seconds), 0.001)
    timeout = httpx.Timeout(effective_timeout)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            trust_env=False,
        ) as client:
            response = await asyncio.wait_for(
                client.request(
                    method,
                    url,
                    json=json,
                ),
                timeout=effective_timeout,
            )
    except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "message": "Downstream service timed out.",
                "url": url,
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Downstream service is unavailable.",
                "url": url,
                "error": str(exc),
            },
        ) from exc

    if response.status_code >= 400:
        try:
            downstream_detail: Any = response.json()
        except ValueError:
            downstream_detail = response.text

        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": "Downstream service rejected the request.",
                "url": url,
                "downstream": downstream_detail,
            },
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Downstream service returned invalid JSON.",
                "url": url,
            },
        ) from exc