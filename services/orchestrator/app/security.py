from __future__ import annotations

from hmac import compare_digest

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


PUBLIC_PATHS = frozenset({"/", "/health", "/health/ready", "/docs", "/redoc", "/openapi.json"})
OWNER_PREFIXES = (
    "/v1/developer",
    "/v1/self-improvement",
    "/v1/owner",
    "/v1/recovery/runs/",
    "/v1/agent/projects/",
)


def _header_token(request: Request, *, owner: bool = False) -> str:
    if owner:
        return request.headers.get("X-AI-Engine-Owner-Token", "").strip()
    explicit = request.headers.get("X-AI-Engine-Token", "").strip()
    if explicit:
        return explicit
    authorization = request.headers.get("Authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.casefold() == "bearer":
        return value.strip()
    return ""


class ControlPlaneAuthMiddleware(BaseHTTPMiddleware):
    """Protect the Orchestrator control plane without affecting health probes."""

    def __init__(
        self,
        app,
        *,
        required: bool,
        control_token: str | None,
        owner_token: str | None,
    ) -> None:
        super().__init__(app)
        self.required = bool(required)
        self.control_token = (control_token or "").strip()
        self.owner_token = (owner_token or "").strip()

    @staticmethod
    def _owner_required(path: str) -> bool:
        return any(path == prefix or path.startswith(prefix + "/") for prefix in OWNER_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        if not self.required or request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if not self.control_token:
            return JSONResponse(
                {"detail": "Control-plane authentication is not configured."},
                status_code=503,
            )
        if not compare_digest(_header_token(request), self.control_token):
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if self._owner_required(request.url.path):
            if not self.owner_token:
                return JSONResponse(
                    {"detail": "Owner authorization is not configured."},
                    status_code=503,
                )
            if not compare_digest(_header_token(request, owner=True), self.owner_token):
                return JSONResponse(
                    {"detail": "Owner authorization required."},
                    status_code=403,
                )
        return await call_next(request)


__all__ = ["ControlPlaneAuthMiddleware"]
