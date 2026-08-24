from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

EventHandler = Callable[["DomainEvent"], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    entity_type: str
    entity_id: UUID
    actor_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventBus:
    """In-process domain event bus. Replace the publisher later without changing services."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._wildcard: list[EventHandler] = []

    def subscribe(self, event_name: str | None, handler: EventHandler) -> None:
        if event_name is None:
            self._wildcard.append(handler)
            return
        self._handlers.setdefault(event_name, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = list(self._wildcard)
        handlers.extend(self._handlers.get(event.name, []))
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "domain_event_handler_failed",
                    event=event.name,
                    entity_type=event.entity_type,
                    entity_id=str(event.entity_id),
                )

    async def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            await publish_event(event)


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus


def enqueue_event(session: Any, event: DomainEvent) -> None:
    events: list[DomainEvent] = session.info.setdefault("domain_events", [])
    events.append(event)


async def publish_event(event: DomainEvent) -> None:
    await get_event_bus().publish(event)
