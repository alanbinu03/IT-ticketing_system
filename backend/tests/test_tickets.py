from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.config import get_settings
from tests.conftest import auth_header, login


async def _tokens(client: AsyncClient, role: str) -> dict:
    settings = get_settings()
    mapping = {
        "admin": (settings.seed_admin_email, settings.seed_admin_password),
        "employee": (settings.seed_employee_email, settings.seed_employee_password),
    }
    email, password = mapping[role]
    return await login(client, email, password)


async def _create_ticket(client: AsyncClient, token: str, **overrides) -> dict:
    payload = {
        "title": f"Cannot connect to VPN {uuid4().hex[:8]}",
        "description": "VPN client fails after the latest Windows update.",
        "priority": "HIGH",
        "severity": "MEDIUM",
        **overrides,
    }
    response = await client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_employee_creates_and_lists_own_ticket(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    assert created["ticket_number"].startswith("IT-")
    assert created["status"] == "NEW"
    assert created["requester"]["email"] == get_settings().seed_employee_email

    listed = await client.get("/api/v1/tickets", headers=auth_header(employee["access_token"]))
    assert listed.status_code == 200
    numbers = {item["ticket_number"] for item in listed.json()["items"]}
    assert created["ticket_number"] in numbers

    fetched = await client.get(
        f"/api/v1/tickets/{created['id']}", headers=auth_header(employee["access_token"])
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_employee_cannot_view_unauthorized_ticket(client: AsyncClient) -> None:
    admin = await _tokens(client, "admin")
    other = await _create_ticket(client, admin["access_token"], title=f"Admin only {uuid4().hex[:8]}")
    employee = await _tokens(client, "employee")
    response = await client.get(
        f"/api/v1/tickets/{other['id']}", headers=auth_header(employee["access_token"])
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    listed = await client.get("/api/v1/tickets", headers=auth_header(employee["access_token"]))
    numbers = {item["id"] for item in listed.json()["items"]}
    assert other["id"] not in numbers


@pytest.mark.asyncio
async def test_admin_sees_unassigned_and_can_assign(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    admin = await _tokens(client, "admin")
    me = await client.get("/api/v1/users/me", headers=auth_header(admin["access_token"]))
    assert me.status_code == 200

    visible = await client.get(
        f"/api/v1/tickets/{created['id']}", headers=auth_header(admin["access_token"])
    )
    assert visible.status_code == 200

    assigned = await client.post(
        f"/api/v1/tickets/{created['id']}/assign",
        json={"agent_id": me.json()["id"], "version": created["version"]},
        headers=auth_header(admin["access_token"]),
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["status"] == "ASSIGNED"
    assert body["assigned_agent"]["id"] == me.json()["id"]

    history = await client.get(
        f"/api/v1/tickets/{created['id']}/history", headers=auth_header(admin["access_token"])
    )
    assert history.status_code == 200
    assert history.json()["assignments"]
    statuses = [row["to_status"] for row in history.json()["status_history"]]
    assert "NEW" in statuses
    assert "ASSIGNED" in statuses


@pytest.mark.asyncio
async def test_workflow_valid_and_invalid_transitions(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    admin = await _tokens(client, "admin")
    me = (await client.get("/api/v1/users/me", headers=auth_header(admin["access_token"]))).json()
    assigned = await client.post(
        f"/api/v1/tickets/{created['id']}/assign",
        json={"agent_id": me["id"]},
        headers=auth_header(admin["access_token"]),
    )
    ticket = assigned.json()

    progressed = await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"status": "IN_PROGRESS", "version": ticket["version"]},
        headers=auth_header(admin["access_token"]),
    )
    assert progressed.status_code == 200
    resolved = await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={
            "status": "RESOLVED",
            "resolution_summary": "Restarted the VPN client and flushed DNS.",
            "version": progressed.json()["version"],
        },
        headers=auth_header(admin["access_token"]),
    )
    assert resolved.status_code == 200
    closed = await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"status": "CLOSED", "version": resolved.json()["version"]},
        headers=auth_header(admin["access_token"]),
    )
    assert closed.status_code == 200

    invalid = await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"status": "IN_PROGRESS", "version": closed.json()["version"]},
        headers=auth_header(admin["access_token"]),
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_employee_can_reopen_resolved_ticket(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    admin = await _tokens(client, "admin")
    me = (await client.get("/api/v1/users/me", headers=auth_header(admin["access_token"]))).json()
    await client.post(
        f"/api/v1/tickets/{created['id']}/assign",
        json={"agent_id": me["id"]},
        headers=auth_header(admin["access_token"]),
    )
    await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_header(admin["access_token"]),
    )
    await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"status": "RESOLVED", "resolution_summary": "Fixed."},
        headers=auth_header(admin["access_token"]),
    )
    reopened = await client.post(
        f"/api/v1/tickets/{created['id']}/status",
        json={"status": "REOPENED", "reason": "Issue returned after reboot."},
        headers=auth_header(employee["access_token"]),
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "REOPENED"


@pytest.mark.asyncio
async def test_comments_and_internal_notes_hidden_from_employee(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    public = await client.post(
        f"/api/v1/tickets/{created['id']}/comments",
        json={"body": "I already tried restarting.", "type": "PUBLIC_COMMENT"},
        headers=auth_header(employee["access_token"]),
    )
    assert public.status_code == 201, public.text

    admin = await _tokens(client, "admin")
    note = await client.post(
        f"/api/v1/tickets/{created['id']}/comments",
        json={"body": "Looks like a certificate issue.", "type": "INTERNAL_NOTE"},
        headers=auth_header(admin["access_token"]),
    )
    assert note.status_code == 201, note.text

    employee_comments = await client.get(
        f"/api/v1/tickets/{created['id']}/comments",
        headers=auth_header(employee["access_token"]),
    )
    assert employee_comments.status_code == 200
    types = {item["type"] for item in employee_comments.json()}
    assert "PUBLIC_COMMENT" in types
    assert "INTERNAL_NOTE" not in types
    assert all("certificate" not in item["body"].lower() for item in employee_comments.json())

    employee_timeline = await client.get(
        f"/api/v1/tickets/{created['id']}/timeline",
        headers=auth_header(employee["access_token"]),
    )
    assert employee_timeline.status_code == 200
    assert all(event.get("comment_type") != "INTERNAL_NOTE" for event in employee_timeline.json())

    agent_comments = await client.get(
        f"/api/v1/tickets/{created['id']}/comments",
        headers=auth_header(admin["access_token"]),
    )
    assert {item["type"] for item in agent_comments.json()} == {"PUBLIC_COMMENT", "INTERNAL_NOTE"}


@pytest.mark.asyncio
async def test_ticket_filtering_and_keyword_search(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    token = employee["access_token"]
    marker = uuid4().hex[:8]
    await _create_ticket(client, token, title=f"Printer jam {marker}", priority="LOW")
    await _create_ticket(client, token, title=f"Payroll outage {marker}", priority="CRITICAL")

    filtered = await client.get(
        "/api/v1/tickets",
        params={"priority": "CRITICAL", "q": marker},
        headers=auth_header(token),
    )
    assert filtered.status_code == 200
    items = filtered.json()["items"]
    assert items
    assert all(item["priority"] == "CRITICAL" for item in items)
    assert all(marker in item["title"] for item in items)


@pytest.mark.asyncio
async def test_ticket_created_writes_audit(client: AsyncClient, db_session: AsyncSession) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "ticket.created",
            AuditLog.entity_id == created["id"],
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.entity_type == "ticket"


@pytest.mark.asyncio
async def test_ticket_summary_hides_queue_counts_for_employees(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    await _create_ticket(client, employee["access_token"])
    employee_summary = await client.get(
        "/api/v1/tickets/summary", headers=auth_header(employee["access_token"])
    )
    assert employee_summary.status_code == 200
    body = employee_summary.json()
    assert body["my_tickets"] >= 1
    assert body["open_mine"] >= 1
    assert body["assigned_to_me"] is None
    assert body["unassigned"] is None

    admin = await _tokens(client, "admin")
    admin_summary = await client.get(
        "/api/v1/tickets/summary", headers=auth_header(admin["access_token"])
    )
    assert admin_summary.status_code == 200
    admin_body = admin_summary.json()
    assert admin_body["assigned_to_me"] is not None
    assert admin_body["unassigned"] is not None


@pytest.mark.asyncio
async def test_employee_cannot_add_internal_note(client: AsyncClient) -> None:
    employee = await _tokens(client, "employee")
    created = await _create_ticket(client, employee["access_token"])
    response = await client.post(
        f"/api/v1/tickets/{created['id']}/comments",
        json={"body": "secret", "type": "INTERNAL_NOTE"},
        headers=auth_header(employee["access_token"]),
    )
    assert response.status_code == 403
