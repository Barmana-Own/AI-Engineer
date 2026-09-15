from fastapi import APIRouter

from app.config import settings
from app.models import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        workspace_root=settings.workspace_root,
    )
