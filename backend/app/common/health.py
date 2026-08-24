from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.common.redis import get_redis
from app.database.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    checks: dict[str, str] = {}
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"
    try:
        client = await get_redis()
        await client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    if all(value == "ok" for value in checks.values()):
        return {"status": "ready", "checks": checks}

    from fastapi import HTTPException

    raise HTTPException(
        status_code=503,
        detail={"error": {"code": "NOT_READY", "message": "One or more dependencies are unavailable."}},
    )
