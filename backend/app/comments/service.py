from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext
from app.comments.models import TicketComment
from app.comments.repository import CommentRepository
from app.comments.schemas import CommentCreate
from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import ForbiddenError, NotFoundError
from app.tickets.access import ensure_can_view
from app.tickets.enums import CommentType
from app.tickets.repository import TicketRepository


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CommentRepository(session)
        self.tickets = TicketRepository(session)

    async def list_for_ticket(self, ticket_id: UUID, auth: AuthContext) -> list[TicketComment]:
        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        ensure_can_view(auth, ticket)
        return await self.repo.list_for_ticket(
            ticket_id, include_internal=auth.has("ticket.internal_note")
        )

    async def add(self, ticket_id: UUID, data: CommentCreate, auth: AuthContext) -> TicketComment:
        ticket = await self.tickets.get_for_update(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        ensure_can_view(auth, ticket)
        if data.type == CommentType.INTERNAL_NOTE:
            if not auth.has("ticket.internal_note"):
                raise ForbiddenError("You cannot add internal notes.")
        elif not auth.has("ticket.comment"):
            raise ForbiddenError()
        comment = TicketComment(
            ticket_id=ticket.id,
            author_id=auth.user.id,
            body=data.body.strip(),
            type=data.type.value,
        )
        await self.repo.add(comment)
        if (
            data.type == CommentType.PUBLIC_COMMENT
            and ticket.first_response_at is None
            and auth.user.id != ticket.requester_id
        ):
            ticket.first_response_at = datetime.now(UTC)
            ticket.updated_by = auth.user.id
        enqueue_event(
            self.session,
            DomainEvent(
                name="ticket.comment_added",
                entity_type="ticket",
                entity_id=ticket.id,
                actor_id=auth.user.id,
                payload={
                    "new": {
                        "comment_id": str(comment.id),
                        "type": comment.type,
                    }
                },
            ),
        )
        await self.session.flush()
        loaded = await self.repo.get_by_id(comment.id)
        assert loaded is not None
        return loaded
