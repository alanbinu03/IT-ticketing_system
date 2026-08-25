from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.email.models import EmailDelivery
from app.email.service import EmailService, get_outbox
from app.users.models import User
from tests.conftest import auth_header, login, unique_email


@pytest.mark.asyncio
async def test_self_registration_is_disabled(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register/request-otp", json={"email": unique_email("signup")}
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "REGISTRATION_DISABLED"


@pytest.mark.asyncio
async def test_unknown_email_cannot_login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email("missing"), "password": "ValidPass123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_wrong_password_cannot_login(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.seed_employee_email, "password": "WrongPass123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_admin_import_csv_then_user_can_login(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    settings = get_settings()
    admin = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    email = unique_email("sheet")
    csv_body = f"name,email,password\nAlex Rivera,{email},ChangeMe!New123\n"
    imported = await client.post(
        "/api/v1/users/import",
        headers=auth_header(admin["access_token"]),
        files={"file": ("users.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["created"] == 1
    assert body["skipped"] == 0

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    assert user.full_name == "Alex Rivera"

    tokens = await login(client, email, "ChangeMe!New123")
    assert tokens["user"]["email"] == email
    assert tokens["user"]["roles"] == ["Employee"]
    assert "admin.portal.access" not in tokens["user"]["permissions"]


@pytest.mark.asyncio
async def test_login_accepts_spaced_and_display_name_email(client: AsyncClient) -> None:
    settings = get_settings()
    spaced = f"  {settings.seed_employee_email.replace('@', ' @ ')}  "
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": spaced, "password": settings.seed_employee_password},
    )
    assert response.status_code == 200, response.text
    wrapped = f"Employee Name <{settings.seed_employee_email}>"
    wrapped_login = await client.post(
        "/api/v1/auth/login",
        json={"email": wrapped, "password": settings.seed_employee_password},
    )
    assert wrapped_login.status_code == 200, wrapped_login.text


@pytest.mark.asyncio
async def test_admin_create_user_accepts_display_name_email(client: AsyncClient) -> None:
    settings = get_settings()
    admin = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    email = unique_email("create")
    created = await client.post(
        "/api/v1/users",
        headers=auth_header(admin["access_token"]),
        json={
            "email": f"New Person < {email} >",
            "password": "ValidPass123",
            "full_name": "New Person",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["email"] == email
    tokens = await login(client, f" {email} ", "ValidPass123")
    assert tokens["user"]["email"] == email


@pytest.mark.asyncio
async def test_import_short_password_is_not_called_invalid_email(client: AsyncClient) -> None:
    settings = get_settings()
    admin = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    email = unique_email("shortpw")
    csv_body = f"name,email,password\nShort Pass,{email},abc\n"
    imported = await client.post(
        "/api/v1/users/import",
        headers=auth_header(admin["access_token"]),
        files={"file": ("users.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["created"] == 0
    assert body["errors"]
    assert "Password" in body["errors"][0]["message"]


@pytest.mark.asyncio
async def test_employee_cannot_import_users(client: AsyncClient) -> None:
    settings = get_settings()
    employee = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    response = await client.post(
        "/api/v1/users/import",
        headers=auth_header(employee["access_token"]),
        files={"file": ("users.csv", b"name,email,password\nA,a@example.com,ValidPass123\n", "text/csv")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employee_admin_login_denied(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": settings.seed_employee_email, "password": settings.seed_employee_password},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_admin_can_use_admin_login(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": settings.seed_admin_email, "password": settings.seed_admin_password},
    )
    assert response.status_code == 200, response.text
    assert "admin.portal.access" in response.json()["user"]["permissions"]


@pytest.mark.asyncio
async def test_employee_cannot_access_admin_users_api(client: AsyncClient) -> None:
    settings = get_settings()
    employee = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    response = await client.get("/api/v1/users", headers=auth_header(employee["access_token"]))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_new_ticket_queues_admin_email(client: AsyncClient, db_session: AsyncSession) -> None:
    settings = get_settings()
    employee = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    created = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Printer jammed in finance",
            "description": "The office printer will not print invoices.",
            "priority": "HIGH",
            "severity": "MEDIUM",
        },
        headers=auth_header(employee["access_token"]),
    )
    assert created.status_code == 201, created.text
    number = created.json()["ticket_number"]
    admin = await login(client, settings.seed_admin_email, settings.seed_admin_password)
    notes = await client.get(
        "/api/v1/notifications",
        params={"unread_only": True, "limit": 20},
        headers=auth_header(admin["access_token"]),
    )
    assert notes.status_code == 200, notes.text
    assert any(number in item["title"] for item in notes.json()["items"])
    assert any(number in item.body for item in get_outbox())
    deliveries = await db_session.execute(
        select(EmailDelivery).where(EmailDelivery.entity_id == created.json()["id"])
    )
    rows = list(deliveries.scalars())
    assert rows
    assert all(row.status in {"QUEUED", "SENT"} for row in rows)


@pytest.mark.asyncio
async def test_smtp_failure_does_not_fail_ticket(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(EmailService, "send", boom)
    settings = get_settings()
    employee = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    created = await client.post(
        "/api/v1/tickets",
        json={
            "title": "VPN down for the floor",
            "description": "Nobody can connect.",
            "priority": "CRITICAL",
            "severity": "HIGH",
        },
        headers=auth_header(employee["access_token"]),
    )
    assert created.status_code == 201, created.text


@pytest.mark.asyncio
async def test_email_service_skips_mailer_in_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("Nodemailer should not be called during tests")

    monkeypatch.setattr(EmailService, "_post_mailer", boom)
    await EmailService.send("signup@example.com", "Verify", "code 123456")
    assert get_outbox()[-1].to_email == "signup@example.com"


@pytest.mark.asyncio
async def test_email_service_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("Nodemailer should not be called while email is disabled")

    monkeypatch.setattr("app.email.service.get_settings", lambda: type("S", (), {
        "email_sending_enabled": False,
        "email_enabled": False,
        "smtp_host": "smtp.gmail.com",
        "app_env": "development",
        "mailer_url": "http://127.0.0.1:3010",
        "mailer_token": "",
    })())
    monkeypatch.setattr(EmailService, "_post_mailer", boom)
    await EmailService.send("ops@example.com", "Ticket", "body")
    assert get_outbox()[-1].to_email == "ops@example.com"


@pytest.mark.asyncio
async def test_duplicate_ticket_email_is_idempotent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from uuid import UUID

    from app.email.queue import enqueue_email

    settings = get_settings()
    employee = await login(client, settings.seed_employee_email, settings.seed_employee_password)
    created = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Duplicate notify check",
            "description": "Used only to test email idempotency.",
            "priority": "LOW",
            "severity": "LOW",
        },
        headers=auth_header(employee["access_token"]),
    )
    ticket_id = UUID(created.json()["id"])
    first = await enqueue_email(
        email_type="ticket.created",
        recipient=settings.seed_admin_email,
        entity_type="ticket",
        entity_id=ticket_id,
        subject="dup",
        body="dup",
    )
    second = await enqueue_email(
        email_type="ticket.created",
        recipient=settings.seed_admin_email,
        entity_type="ticket",
        entity_id=ticket_id,
        subject="dup",
        body="dup",
    )
    assert first is not None and second is not None
    assert first.id == second.id
