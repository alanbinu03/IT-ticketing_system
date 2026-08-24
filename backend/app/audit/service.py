from __future__ import annotations

from typing import Any
from uuid import UUID

from app.audit.repository import AuditRepository, audit_from_event
from app.common.events import DomainEvent, get_event_bus
from app.database.session import get_session_factory


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


SKIP_AUDIT = {"user.logged_in"}
_registered = False


async def persist_audit_event(event: DomainEvent) -> None:
    if event.name in SKIP_AUDIT:
        return
    safe = DomainEvent(
        name=event.name,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        actor_id=event.actor_id,
        payload=_json_safe(event.payload),
        occurred_at=event.occurred_at,
    )
    factory = get_session_factory()
    async with factory() as session:
        await AuditRepository(session).add(audit_from_event(safe))
        await session.commit()


def register_audit_handler() -> None:
    global _registered
    if _registered:
        return
    get_event_bus().subscribe(None, persist_audit_event)
    _registered = True
