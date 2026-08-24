from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification
from app.roles.constants import ROLE_ADMIN
from app.roles.models import Role, UserRole
from app.users.models import User


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.read_at.is_(None))
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(Notification).where(*filters)
                )
            ).scalar_one()
        )
        rows = await self.session.execute(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total

    async def unread_count(self, user_id: UUID) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(Notification)
                    .where(Notification.user_id == user_id, Notification.read_at.is_(None))
                )
            ).scalar_one()
        )

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None
        if item.read_at is None:
            item.read_at = datetime.now(UTC)
            await self.session.flush()
        return item

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        return int(result.rowcount or 0)

    async def list_active_admins(self) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.name == ROLE_ADMIN,
                User.is_active.is_(True),
                User.is_verified.is_(True),
            )
            .order_by(User.full_name)
        )
        return list(result.scalars().unique().all())
