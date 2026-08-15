from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db

router = APIRouter(tags=["health"])
root_router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@root_router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@root_router.get("/readyz")
async def readyz(session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    try:
        get_settings().validate_runtime()
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Service not ready: {type(exc).__name__}") from exc
    return {"status": "ready"}
