from __future__ import annotations

from typing import Any

from app.common.events import DomainEvent, get_event_bus
from app.config import get_settings
from app.database.session import get_session_factory
from app.email.queue import enqueue_email
from app.email.service import render_template
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository

_registered = False


def _ticket_payload(event: DomainEvent) -> dict[str, Any]:
    payload = event.payload or {}
    new = payload.get("new")
    return new if isinstance(new, dict) else {}


async def notify_admins_on_ticket_created(event: DomainEvent) -> None:
    if event.name != "ticket.created":
        return
    data = _ticket_payload(event)
    number = str(data.get("ticket_number") or "")
    title = str(data.get("title") or "New ticket")
    requester = str(data.get("requester_name") or "An employee")
    requester_email = str(data.get("requester_email") or "")
    priority = str(data.get("priority") or "MEDIUM").replace("_", " ").title()
    category = str(data.get("category") or "Uncategorized")
    created = str(data.get("created") or "")
    actor_id = event.actor_id
    settings = get_settings()
    link = f"{settings.frontend_url.rstrip('/')}/tickets/{event.entity_id}"
    popup_title = f"New ticket {number}".strip()
    popup_body = f"{requester} opened “{title}”."
    subject = f"[{number}] New IT Ticket — {title}" if number else f"New IT Ticket — {title}"
    text_body = (
        "A new IT support ticket has been raised.\n\n"
        f"Ticket:\n{number}\n\n"
        f"Raised By:\n{requester}\n\n"
        f"Email:\n{requester_email}\n\n"
        f"Title:\n{title}\n\n"
        f"Priority:\n{priority}\n\n"
        f"Category:\n{category}\n\n"
        f"Created:\n{created}\n\n"
        f"Open Ticket:\n{link}\n"
    )
    html = render_template(
        "ticket_created_admin.html",
        ticket_number=number,
        requester_name=requester,
        requester_email=requester_email,
        title=title,
        priority=priority,
        category=category,
        created=created,
        ticket_url=link,
    )

    factory = get_session_factory()
    mail_targets: list[str] = []
    async with factory() as session:
        repo = NotificationRepository(session)
        admins = await repo.list_active_admins()
        recipients = [admin for admin in admins if actor_id is None or admin.id != actor_id]
        mail_targets = [admin.email.lower() for admin in recipients]
        for extra in settings.it_notification_email_list:
            if extra not in mail_targets:
                mail_targets.append(extra)
        for admin in recipients:
            await repo.add(
                Notification(
                    user_id=admin.id,
                    type="ticket.created",
                    title=popup_title or "New ticket",
                    body=popup_body,
                    link=f"/tickets/{event.entity_id}",
                    ticket_id=event.entity_id,
                )
            )
        await session.commit()

    for email in mail_targets:
        try:
            await enqueue_email(
                email_type="ticket.created",
                recipient=email,
                entity_type="ticket",
                entity_id=event.entity_id,
                subject=subject,
                body=text_body,
                html=html,
            )
        except Exception:
            import structlog

            structlog.get_logger(__name__).exception("ticket_email_enqueue_failed", recipient=email)


def register_notification_handler() -> None:
    global _registered
    if _registered:
        return
    get_event_bus().subscribe("ticket.created", notify_admins_on_ticket_created)
    _registered = True
