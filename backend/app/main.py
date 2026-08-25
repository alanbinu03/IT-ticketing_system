from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.audit.service import register_audit_handler
from app.auth.router import (
    auth_router,
    departments_router,
    permissions_router,
    roles_router,
    teams_router,
    users_router,
)
from app.categories.router import categories_router
from app.common.error_handlers import register_error_handlers
from app.common.health import router as health_router
from app.common.logging import configure_logging
from app.common.middleware import RequestContextMiddleware
from app.common.redis import close_redis, get_redis
from app.config import get_settings
from app.database.session import dispose_engine, get_engine, import_models
from app.email.queue import start_email_worker, stop_email_worker
from app.notifications.handlers import register_notification_handler
from app.notifications.router import notifications_router
from app.tickets.router import tickets_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    import_models()
    register_audit_handler()
    register_notification_handler()
    get_engine()
    try:
        await get_redis()
    except Exception:
        logger.warning("redis_unavailable_at_startup")
    start_email_worker()
    logger.info("application_started", app=settings.app_name, env=settings.app_env)
    yield
    await stop_email_worker()
    await close_redis()
    await dispose_engine()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
    )
    application.add_middleware(RequestContextMiddleware)
    cors_kwargs: dict = {
        "allow_origins": settings.cors_origin_list,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if settings.is_development:
        cors_kwargs["allow_origin_regex"] = (
            r"https?://(localhost|127\.0\.0\.1|\[::1\]|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?"
        )
    application.add_middleware(CORSMiddleware, **cors_kwargs)
    register_error_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(users_router, prefix=settings.api_v1_prefix)
    application.include_router(roles_router, prefix=settings.api_v1_prefix)
    application.include_router(permissions_router, prefix=settings.api_v1_prefix)
    application.include_router(departments_router, prefix=settings.api_v1_prefix)
    application.include_router(teams_router, prefix=settings.api_v1_prefix)
    application.include_router(categories_router, prefix=settings.api_v1_prefix)
    application.include_router(tickets_router, prefix=settings.api_v1_prefix)
    application.include_router(notifications_router, prefix=settings.api_v1_prefix)

    @application.get("/")
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "health": "/health",
            "ready": "/ready",
            "api": settings.api_v1_prefix,
            "docs": "/docs" if settings.is_development else None,
        }

    @application.get(settings.api_v1_prefix)
    async def api_index() -> dict:
        prefix = settings.api_v1_prefix
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "endpoints": {
                "login": f"{prefix}/auth/login",
                "me": f"{prefix}/users/me",
                "tickets": f"{prefix}/tickets",
                "ticket_summary": f"{prefix}/tickets/summary",
                "categories": f"{prefix}/categories",
                "notifications": f"{prefix}/notifications",
            },
        }

    return application


app = create_app()
