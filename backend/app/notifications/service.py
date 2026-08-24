from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def list(
        self,
        user_id: UUID,
        *,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int, int]:
        items, total = await self.repo.list_for_user(
            user_id, unread_only=unread_only, limit=limit, offset=offset
        )
        unread = await self.repo.unread_count(user_id)
        return items, total, unread

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        item = await self.repo.mark_read(notification_id, user_id)
        if item is None:
            raise NotFoundError("Notification not found.")
        return item

    async def mark_all_read(self, user_id: UUID) -> int:
        return await self.repo.mark_all_read(user_id)
