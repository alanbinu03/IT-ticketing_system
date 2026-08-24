from __future__ import annotations

import json
from uuid import UUID

import structlog

from app.common.redis import get_redis
from app.config import get_settings

logger = structlog.get_logger(__name__)

CACHE_PREFIX = "rbac:user:"


async def cache_user_permissions(user_id: UUID, codes: set[str]) -> None:
    try:
        client = await get_redis()
        await client.set(
            f"{CACHE_PREFIX}{user_id}",
            json.dumps(sorted(codes)),
            ex=get_settings().rbac_cache_ttl_seconds,
        )
    except Exception:
        logger.warning("rbac_cache_write_failed", user_id=str(user_id))


async def load_cached_permissions(user_id: UUID) -> set[str] | None:
    try:
        client = await get_redis()
        raw = await client.get(f"{CACHE_PREFIX}{user_id}")
        if raw:
            return set(json.loads(raw))
    except Exception:
        logger.warning("rbac_cache_read_failed", user_id=str(user_id))
    return None


async def invalidate_user_permission_cache(user_id: UUID) -> None:
    try:
        client = await get_redis()
        await client.delete(f"{CACHE_PREFIX}{user_id}")
    except Exception:
        logger.warning("rbac_cache_invalidate_failed", user_id=str(user_id))


async def invalidate_role_permission_cache() -> None:
    try:
        client = await get_redis()
        async for key in client.scan_iter(match=f"{CACHE_PREFIX}*"):
            await client.delete(key)
    except Exception:
        logger.warning("rbac_cache_role_invalidate_failed")
