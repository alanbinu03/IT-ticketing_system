from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerification
from app.config import get_settings
from app.email.models import EmailDelivery
from app.email.service import EmailService, get_outbox
from app.users.models import User
from tests.conftest import auth_header, login, unique_email


def latest_otp(email: str) -> str:
    for item in reversed(get_outbox()):
        if item.to_email == email:
            match = re.search(r"\b(\d{6})\b", item.body)
            if match:
                return match.group(1)
    raise AssertionError(f"No OTP email found for {email}")


async def register_employee(client: AsyncClient, email: str, password: str = "ChangeMe!New123") -> None:
    started = await client.post("/api/v1/auth/register/request-otp", json={"email": email})
    assert started.status_code == 200, started.text
    verified = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": latest_otp(email)},
    )
    assert verified.status_code == 200, verified.text
    completed = await client.post(
        "/api/v1/auth/register/complete",
        json={
            "registration_token": verified.json()["registration_token"],
            "full_name": "Alex Rivera",
            "password": password,
            "role": "SYSTEM_ADMIN",
        },
    )
    assert completed.status_code == 200, completed.text


@pytest.mark.asyncio
async def test_register_requires_valid_email(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register/request-otp", json={"email": "not-an-email"})
    assert response.status_code in {400, 422}


@pytest.mark.asyncio
async def test_register_lists_allowed_domains(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/register/allowed-domains")
    assert response.status_code == 200
    assert "example.com" in response.json()["domains"]
    assert "company.com" in response.json()["domains"]


@pytest.mark.asyncio
async def test_register_rejects_public_and_fake_domains(client: AsyncClient) -> None:
    for email in ("person@gmail.com", "person@yahoo.com", "attacker@company.com.fake-domain.com"):
        response = await client.post("/api/v1/auth/register/request-otp", json={"email": email})
        assert response.status_code == 400, email
        body = response.json()["error"]
        assert body["code"] == "EMAIL_DOMAIN_NOT_ALLOWED"
        assert "@example.com" in body["message"] or "company email" in body["message"].lower()


@pytest.mark.asyncio
async def test_register_accepts_company_and_example_domains(client: AsyncClient) -> None:
    email = f"yash-{unique_email('co').split('@')[0]}@company.com"
    response = await client.post("/api/v1/auth/register/request-otp", json={"email": email})
    assert response.status_code == 200, response.text
    assert "verification code" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_employee_register_verify_complete_and_login(client: AsyncClient, db_session: AsyncSession) -> None:
    email = unique_email("signup")
    await register_employee(client, email)
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    await db_session.refresh(user)
    assert user.email_is_verified is True

    tokens = await login(client, email, "ChangeMe!New123")
    assert tokens["user"]["email"] == email
    assert tokens["user"]["roles"] == ["Employee"]
    assert "admin.portal.access" not in tokens["user"]["permissions"]


@pytest.mark.asyncio
async def test_duplicate_registration_is_generic(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.post(
        "/api/v1/auth/register/request-otp",
        json={"email": settings.seed_employee_email},
    )
    assert response.status_code == 200
    assert "If the email is eligible" in response.json()["message"]


@pytest.mark.asyncio
async def test_incorrect_and_expired_otp_and_reuse(client: AsyncClient, db_session: AsyncSession) -> None:
    email = unique_email("otp")
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})
    wrong = await client.post("/api/v1/auth/register/verify-otp", json={"email": email, "otp": "000000"})
    assert wrong.status_code == 401

    otp = latest_otp(email)
    first = await client.post("/api/v1/auth/register/verify-otp", json={"email": email, "otp": otp})
    assert first.status_code == 200
    reused = await client.post("/api/v1/auth/register/verify-otp", json={"email": email, "otp": otp})
    assert reused.status_code == 401

    expired_email = unique_email("expired")
    await client.post("/api/v1/auth/register/request-otp", json={"email": expired_email})
    result = await db_session.execute(
        select(EmailVerification)
        .where(EmailVerification.email == expired_email)
        .order_by(EmailVerification.created_at.desc())
    )
    record = result.scalars().first()
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()
    expired = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": expired_email, "otp": latest_otp(expired_email)},
    )
    assert expired.status_code == 401


@pytest.mark.asyncio
async def test_otp_attempt_limit(client: AsyncClient) -> None:
    email = unique_email("limit")
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})
    for _ in range(5):
        await client.post("/api/v1/auth/register/verify-otp", json={"email": email, "otp": "111111"})
    blocked = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": latest_otp(email)},
    )
    assert blocked.status_code == 401


@pytest.mark.asyncio
async def test_cannot_complete_without_verification(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register/complete",
        json={
            "registration_token": "not-a-real-token-value-here",
            "full_name": "Alex Rivera",
            "password": "ChangeMe!New123",
        },
    )
    assert response.status_code == 401


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
async def test_smtp_failure_does_not_fail_ticket(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
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
async def test_duplicate_ticket_email_is_idempotent(client: AsyncClient, db_session: AsyncSession) -> None:
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
