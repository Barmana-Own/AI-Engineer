from __future__ import annotations

from hmac import compare_digest

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


PUBLIC_PATHS = frozenset({"/", "/health", "/health/ready", "/docs", "/redoc", "/openapi.json"})


def _header_token(request: Request) -> str:
    explicit = request.headers.get("X-AI-Engine-Token", "").strip()
    if explicit:
        return explicit
    authorization = request.headers.get("Authorization", "")
    scheme, _, value = authorization.partition(" ")
    return value.strip() if scheme.casefold() == "bearer" else ""


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """Prevent public, anonymous consumption of model-provider quota."""

    def __init__(self, app, *, required: bool, token: str | None) -> None:
        super().__init__(app)
        self.required = bool(required)
        self.token = (token or "").strip()

    async def dispatch(self, request: Request, call_next):
        if not self.required or request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        if not self.token:
            return JSONResponse(
                {"detail": "Gateway authentication is not configured."},
                status_code=503,
            )
        if not compare_digest(_header_token(request), self.token):
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)


__all__ = ["GatewayAuthMiddleware"]
