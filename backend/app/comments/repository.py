from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.comments.models import TicketComment


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, comment: TicketComment) -> TicketComment:
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def get_by_id(self, comment_id: UUID) -> TicketComment | None:
        result = await self.session.execute(
            select(TicketComment)
            .options(selectinload(TicketComment.author))
            .where(TicketComment.id == comment_id)
        )
        return result.scalar_one_or_none()

    async def list_for_ticket(
        self, ticket_id: UUID, *, include_internal: bool
    ) -> list[TicketComment]:
        stmt = (
            select(TicketComment)
            .options(selectinload(TicketComment.author))
            .where(TicketComment.ticket_id == ticket_id)
            .order_by(TicketComment.created_at.asc())
        )
        if not include_internal:
            stmt = stmt.where(TicketComment.type != "INTERNAL_NOTE")
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
