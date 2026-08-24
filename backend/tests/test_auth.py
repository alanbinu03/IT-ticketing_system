from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.config import get_settings
from tests.conftest import auth_header, login


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["postgres"] == "ok"
    assert body["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    settings = get_settings()
    data = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] == settings.access_token_expire_minutes * 60
    assert data["user"]["email"] == settings.seed_admin_email
    assert "Admin" in data["user"]["roles"]
    assert "user.create" in data["user"]["permissions"]


@pytest.mark.asyncio
async def test_login_rejects_bad_password(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.seed_admin_email, "password": "wrong-password"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_user_same_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "whatever12"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient) -> None:
    settings = get_settings()
    tokens = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    response = await client.get("/api/v1/users/me", headers=auth_header(tokens["access_token"]))
    assert response.status_code == 200
    assert response.json()["email"] == settings.seed_admin_email
    assert "permissions" in response.json()


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient) -> None:
    settings = get_settings()
    tokens = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    first_refresh = tokens["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != first_refresh
    assert rotated["access_token"]

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    settings = get_settings()
    tokens = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    logout = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout.status_code == 204
    refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401
