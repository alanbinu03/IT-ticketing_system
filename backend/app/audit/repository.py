from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.common.events import DomainEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, log: AuditLog) -> AuditLog:
        self.session.add(log)
        await self.session.flush()
        return log


def audit_from_event(event: DomainEvent) -> AuditLog:
    payload = event.payload
    return AuditLog(
        actor_id=event.actor_id,
        action=event.name,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        previous_values=payload.get("previous"),
        new_values=payload.get("new"),
        metadata_={k: v for k, v in payload.items() if k not in {"previous", "new"}} or None,
    )
