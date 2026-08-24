from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.common.events import DomainEvent, enqueue_event, get_event_bus
from app.common.redis import get_redis
from app.config import get_settings
from app.database.session import get_session_factory
from app.email.models import EmailDelivery
from app.email.service import EmailService

logger = structlog.get_logger(__name__)

QUEUE_KEY = "email:jobs"
MAX_ATTEMPTS = 3
_worker_task: asyncio.Task | None = None


def delivery_key(email_type: str, entity_id: UUID, recipient: str) -> str:
    return f"{email_type}:{entity_id}:{recipient.lower().strip()}"


async def enqueue_email(
    *,
    email_type: str,
    recipient: str,
    entity_type: str,
    entity_id: UUID,
    subject: str,
    body: str,
    html: str | None = None,
    session=None,
) -> EmailDelivery | None:
    recipient = recipient.lower().strip()
    key = delivery_key(email_type, entity_id, recipient)
    values = {
        "id": uuid4(),
        "email_type": email_type,
        "recipient": recipient,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": "QUEUED",
        "attempt_count": 0,
        "idempotency_key": key,
    }
    owns_session = session is None
    factory = get_session_factory()
    work = factory() if owns_session else _NullCtx(session)
    async with work as db:
        result = await db.execute(
            pg_insert(EmailDelivery)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(EmailDelivery.id)
        )
        created_id = result.scalar_one_or_none()
        if created_id is None:
            existing = await db.execute(select(EmailDelivery).where(EmailDelivery.idempotency_key == key))
            delivery = existing.scalar_one_or_none()
            if owns_session:
                await db.commit()
            return delivery
        enqueue_event(
            db,
            DomainEvent(
                name="email.queued",
                entity_type=entity_type,
                entity_id=entity_id,
                payload={"recipient": recipient, "email_type": email_type},
            ),
        )
        if owns_session:
            await db.commit()
        delivery = EmailDelivery(**values)
        delivery.id = created_id

    payload = json.dumps(
        {
            "delivery_id": str(created_id),
            "subject": subject,
            "body": body,
            "html": html,
        }
    )
    if get_settings().app_env.lower() == "test":
        await process_job(payload)
        return delivery
    try:
        client = await get_redis()
        await client.lpush(QUEUE_KEY, payload)
    except Exception:
        logger.warning("email_queue_unavailable", delivery_id=str(created_id))
        await process_job(payload)
    return delivery


class _NullCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


async def process_job(raw: str) -> None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    delivery_id = UUID(data["delivery_id"])
    factory = get_session_factory()
    async with factory() as session:
        delivery = await session.get(EmailDelivery, delivery_id)
        if delivery is None or delivery.status == "SENT":
            return
        if delivery.attempt_count >= MAX_ATTEMPTS:
            delivery.status = "FAILED"
            await session.commit()
            return
        delivery.attempt_count += 1
        try:
            await EmailService.send(
                delivery.recipient,
                data["subject"],
                data["body"],
                html=data.get("html"),
            )
            delivery.status = "SENT"
            delivery.sent_at = datetime.now(UTC)
            delivery.last_error = None
            await get_event_bus().publish(
                DomainEvent(
                    name="email.sent",
                    entity_type=delivery.entity_type,
                    entity_id=delivery.entity_id,
                    payload={"recipient": delivery.recipient},
                )
            )
        except Exception as exc:
            delivery.last_error = str(exc)[:500]
            if delivery.attempt_count >= MAX_ATTEMPTS:
                delivery.status = "FAILED"
                await get_event_bus().publish(
                    DomainEvent(
                        name="email.failed",
                        entity_type=delivery.entity_type,
                        entity_id=delivery.entity_id,
                        payload={"recipient": delivery.recipient},
                    )
                )
            else:
                delivery.status = "QUEUED"
        await session.commit()
        if delivery.status == "QUEUED":
            try:
                client = await get_redis()
                await client.lpush(QUEUE_KEY, raw)
            except Exception:
                pass


async def drain_once(limit: int = 20) -> int:
    processed = 0
    try:
        client = await get_redis()
    except Exception:
        return 0
    for _ in range(limit):
        raw = await client.rpop(QUEUE_KEY)
        if not raw:
            break
        await process_job(raw if isinstance(raw, str) else raw.decode())
        processed += 1
    return processed


async def _worker_loop() -> None:
    while True:
        try:
            client = await get_redis()
            item = await client.brpop(QUEUE_KEY, timeout=2)
            if item:
                _key, raw = item
                await process_job(raw if isinstance(raw, str) else raw.decode())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("email_worker_loop_failed")
            await asyncio.sleep(2)


def start_email_worker() -> None:
    global _worker_task
    if get_settings().app_env.lower() == "test":
        return
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop(), name="email-worker")


async def stop_email_worker() -> None:
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
