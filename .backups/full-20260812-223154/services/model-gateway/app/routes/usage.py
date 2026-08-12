from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_usage_store
from app.schemas import UsageSummary
from app.usage import UsageStore

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummary)
async def usage_summary(
    usage_store: UsageStore = Depends(get_usage_store),
) -> UsageSummary:
    return await usage_store.summary()
