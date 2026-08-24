from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.config import get_settings
from app.roles.constants import ROLE_ADMIN, ROLE_EMPLOYEE
from tests.conftest import auth_header, login, unique_email


async def _role_id(client: AsyncClient, token: str, name: str) -> str:
    response = await client.get("/api/v1/roles", headers=auth_header(token))
    assert response.status_code == 200
    match = next(role for role in response.json() if role["name"] == name)
    return match["id"]


async def _department_id(client: AsyncClient, token: str, code: str = "ENG") -> str:
    response = await client.get("/api/v1/departments", headers=auth_header(token))
    assert response.status_code == 200
    match = next(item for item in response.json()["items"] if item["code"] == code)
    return match["id"]


@pytest.mark.asyncio
async def test_employee_cannot_list_or_create_users(client: AsyncClient) -> None:
    settings = get_settings()
    tokens = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    headers = auth_header(tokens["access_token"])
    listed = await client.get("/api/v1/users", headers=headers)
    assert listed.status_code == 403
    assert listed.json()["error"]["code"] == "FORBIDDEN"

    created = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": unique_email("blocked"),
            "password": "ValidPass123",
            "full_name": "Blocked User",
        },
    )
    assert created.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_manage_departments(client: AsyncClient) -> None:
    settings = get_settings()
    tokens = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    response = await client.post(
        "/api/v1/departments",
        headers=auth_header(tokens["access_token"]),
        json={"name": "Should Fail", "code": "NOPE"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_creates_user_with_department_and_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    settings = get_settings()
    tokens = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    token = tokens["access_token"]
    department_id = await _department_id(client, token)
    role_id = await _role_id(client, token, ROLE_EMPLOYEE)
    email = unique_email("created")

    response = await client.post(
        "/api/v1/users",
        headers=auth_header(token),
        json={
            "email": email,
            "password": "ValidPass123",
            "full_name": "Pat Nguyen",
            "department_id": department_id,
            "role_ids": [role_id],
            "employee_code": f"E-{email.split('@')[0][-8:]}",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == email
    assert body["department"]["code"] == "ENG"
    assert ROLE_EMPLOYEE in body["roles"]

    created_login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "ValidPass123"}
    )
    assert created_login.status_code == 200

    logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "user.created").order_by(AuditLog.created_at.desc())
        )
    ).scalars().all()
    assert any(log.entity_id.hex == body["id"].replace("-", "") or str(log.entity_id) == body["id"] for log in logs)


@pytest.mark.asyncio
async def test_admin_can_view_users_employee_cannot_view_other_profile(
    client: AsyncClient,
) -> None:
    settings = get_settings()
    admin = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    admin_id = admin["user"]["id"]
    employee = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    other = await client.get(
        f"/api/v1/users/{admin_id}",
        headers=auth_header(employee["access_token"]),
    )
    assert other.status_code == 403

    own = await client.get(
        f"/api/v1/users/{employee['user']['id']}",
        headers=auth_header(employee["access_token"]),
    )
    assert own.status_code == 200

    listed = await client.get("/api/v1/users", headers=auth_header(admin["access_token"]))
    assert listed.status_code == 200
    assert listed.json()["total"] >= 3


@pytest.mark.asyncio
async def test_assign_roles_and_team_membership(client: AsyncClient) -> None:
    settings = get_settings()
    admin = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    token = admin["access_token"]
    headers = auth_header(token)
    department_id = await _department_id(client, token, "IT")
    admin_role = await _role_id(client, token, ROLE_ADMIN)
    employee_role = await _role_id(client, token, ROLE_EMPLOYEE)
    email = unique_email("adminish")

    created = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": email,
            "password": "ValidPass123",
            "full_name": "Test Role User",
            "department_id": department_id,
            "role_ids": [employee_role],
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    updated_roles = await client.put(
        f"/api/v1/users/{user_id}/roles",
        headers=headers,
        json={"role_ids": [admin_role]},
    )
    assert updated_roles.status_code == 200
    assert ROLE_ADMIN in updated_roles.json()["roles"]
    assert ROLE_EMPLOYEE not in updated_roles.json()["roles"]

    teams = await client.get("/api/v1/teams", headers=headers)
    assert teams.status_code == 200
    network = next(item for item in teams.json()["items"] if item["code"] == "NET")

    member = await client.post(
        f"/api/v1/teams/{network['id']}/members",
        headers=headers,
        json={"user_id": user_id, "is_lead": False},
    )
    assert member.status_code == 200
    assert any(m["user_id"] == user_id for m in member.json()["members"])

    relogin = await login(client, email, "ValidPass123")
    assert ROLE_ADMIN in relogin["user"]["roles"]
    assert "user.view" in relogin["user"]["permissions"]
    assert network["id"] in relogin["user"]["team_ids"]

    restored = await client.put(
        f"/api/v1/users/{user_id}/roles",
        headers=headers,
        json={"role_ids": [employee_role]},
    )
    assert restored.status_code == 200
    disabled = await client.post(f"/api/v1/users/{user_id}/disable", headers=headers)
    assert disabled.status_code == 200
