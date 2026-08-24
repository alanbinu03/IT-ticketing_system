"""SQLAlchemy async engine and session factory.

Connection pooling (one engine per process, never per request):
- pool_size: baseline checked-out connections
- max_overflow: extra connections under burst
- pool_pre_ping: validate before use (avoids stale sockets)
- pool_recycle: recycle before typical idle timeouts (seconds)

Several API replicas times (pool_size + max_overflow) must remain below
PostgreSQL max_connections. PgBouncer can sit in front later without
changing application queries.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.common.events import DomainEvent, get_event_bus

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        kwargs: dict = {
            "pool_pre_ping": settings.db_pool_pre_ping,
            "echo": False,
        }
        if settings.app_env.lower() == "test":
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_size"] = settings.db_pool_size
            kwargs["max_overflow"] = settings.db_max_overflow
            kwargs["pool_recycle"] = settings.db_pool_recycle_seconds
        _engine = create_async_engine(settings.database_url, **kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session. Commit on success, then publish events."""
    factory = get_session_factory()
    async with factory() as session:
        events: list[DomainEvent] = []
        session.info["domain_events"] = events
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            if events:
                await get_event_bus().publish_all(events)


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def import_models() -> None:
    """Import all mapped classes so Alembic and mappers see them."""
    from app.audit import models as audit_models  # noqa: F401
    from app.auth import models as auth_models  # noqa: F401
    from app.categories import models as category_models  # noqa: F401
    from app.comments import models as comment_models  # noqa: F401
    from app.departments import models as department_models  # noqa: F401
    from app.email import models as email_models  # noqa: F401
    from app.notifications import models as notification_models  # noqa: F401
    from app.roles import models as role_models  # noqa: F401
    from app.teams import models as team_models  # noqa: F401
    from app.tickets import models as ticket_models  # noqa: F401
    from app.users import models as user_models  # noqa: F401
