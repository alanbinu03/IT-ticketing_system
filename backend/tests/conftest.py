from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-which-is-32-chars!")
os.environ.setdefault("ALLOWED_EMAIL_DOMAINS", "example.com,company.com,subsidiary.com")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://ticketing:ticketing@localhost:5433/ticketing",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SEED_ADMIN_EMAIL", "hardik@example.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "ChangeMe!Admin123")
os.environ.setdefault("SEED_ADMIN_RONALD_EMAIL", "ronald@example.com")
os.environ.setdefault("SEED_ADMIN_SANJAY_EMAIL", "sanjay@example.com")
os.environ.setdefault("SEED_EMPLOYEE_EMAIL", "employee@example.com")
os.environ.setdefault("SEED_EMPLOYEE_PASSWORD", "ChangeMe!Employee123")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.audit.service import register_audit_handler  # noqa: E402
from app.database.session import get_session_factory, import_models  # noqa: E402
from app.main import app  # noqa: E402
from app.notifications.handlers import register_notification_handler  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrate_and_seed() -> None:
    import_models()
    register_audit_handler()
    register_notification_handler()
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if upgrade.returncode != 0:
        raise RuntimeError(f"alembic upgrade failed:\n{upgrade.stdout}\n{upgrade.stderr}")
    seeded = subprocess.run(
        [sys.executable, "-m", "app.database.seed"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if seeded.returncode != 0:
        raise RuntimeError(f"seed failed:\n{seeded.stdout}\n{seeded.stderr}")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4().hex[:10]}@example.com"
