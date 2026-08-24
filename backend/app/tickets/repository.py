from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, case, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.tickets.enums import PRIORITY_RANK
from app.tickets.models import (
    Tag,
    Ticket,
    TicketAssignment,
    TicketNumberSequence,
    TicketStatusHistory,
    TicketTag,
)


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_relations(self) -> Select[tuple[Ticket]]:
        return select(Ticket).options(
            selectinload(Ticket.requester),
            selectinload(Ticket.department),
            selectinload(Ticket.assigned_team),
            selectinload(Ticket.assigned_agent),
            selectinload(Ticket.category),
            selectinload(Ticket.subcategory),
            selectinload(Ticket.tag_links).selectinload(TicketTag.tag),
        )

    async def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        result = await self.session.execute(self._with_relations().where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()

    async def get_by_number(self, ticket_number: str) -> Ticket | None:
        result = await self.session.execute(
            self._with_relations().where(Ticket.ticket_number == ticket_number.upper())
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, ticket_id: UUID) -> Ticket | None:
        locked = await self.session.execute(
            select(Ticket.id).where(Ticket.id == ticket_id).with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            return None
        cached = await self.session.get(Ticket, ticket_id)
        if cached is not None:
            self.session.expire(cached)
        return await self.get_by_id(ticket_id)

    async def add(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def allocate_ticket_number(self, year: int) -> str:
        await self.session.execute(
            pg_insert(TicketNumberSequence)
            .values(year=year, last_value=0)
            .on_conflict_do_nothing(index_elements=["year"])
        )
        result = await self.session.execute(
            select(TicketNumberSequence).where(TicketNumberSequence.year == year).with_for_update()
        )
        sequence = result.scalar_one()
        sequence.last_value += 1
        await self.session.flush()
        return f"IT-{year}-{sequence.last_value:06d}"

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        visibility,
        statuses: list[str] | None = None,
        priorities: list[str] | None = None,
        requester_id: UUID | None = None,
        assigned_agent_id: UUID | None = None,
        assigned_team_id: UUID | None = None,
        department_id: UUID | None = None,
        category_id: UUID | None = None,
        ticket_number: str | None = None,
        q: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        unassigned: bool | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Ticket], int]:
        filters = select(Ticket)
        if visibility is not None:
            filters = filters.where(visibility)
        if statuses:
            filters = filters.where(Ticket.status.in_(statuses))
        if priorities:
            filters = filters.where(Ticket.priority.in_(priorities))
        if requester_id:
            filters = filters.where(Ticket.requester_id == requester_id)
        if assigned_agent_id:
            filters = filters.where(Ticket.assigned_agent_id == assigned_agent_id)
        if assigned_team_id:
            filters = filters.where(Ticket.assigned_team_id == assigned_team_id)
        if department_id:
            filters = filters.where(Ticket.department_id == department_id)
        if category_id:
            filters = filters.where(
                or_(Ticket.category_id == category_id, Ticket.subcategory_id == category_id)
            )
        if ticket_number:
            filters = filters.where(Ticket.ticket_number.ilike(f"%{ticket_number.strip()}%"))
        if q:
            pattern = f"%{q.strip()}%"
            filters = filters.where(
                or_(
                    Ticket.title.ilike(pattern),
                    Ticket.description.ilike(pattern),
                    Ticket.ticket_number.ilike(pattern),
                )
            )
        if date_from:
            filters = filters.where(Ticket.created_at >= date_from)
        if date_to:
            filters = filters.where(Ticket.created_at <= date_to)
        if unassigned is True:
            filters = filters.where(Ticket.assigned_agent_id.is_(None))

        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(
                        filters.with_only_columns(Ticket.id).subquery()
                    )
                )
            ).scalar_one()
        )

        descending = order.lower() != "asc"
        if sort == "priority":
            rank = case(
                {priority.value: rank for priority, rank in PRIORITY_RANK.items()},
                value=Ticket.priority,
            )
            order_by = rank.desc() if descending else rank.asc()
        elif sort == "updated_at":
            order_by = Ticket.updated_at.desc() if descending else Ticket.updated_at.asc()
        elif sort == "due_at":
            order_by = Ticket.due_at.desc() if descending else Ticket.due_at.asc()
        else:
            order_by = Ticket.created_at.desc() if descending else Ticket.created_at.asc()

        rows = await self.session.execute(
            filters.options(
                selectinload(Ticket.requester),
                selectinload(Ticket.department),
                selectinload(Ticket.assigned_team),
                selectinload(Ticket.assigned_agent),
                selectinload(Ticket.category),
                selectinload(Ticket.subcategory),
                selectinload(Ticket.tag_links).selectinload(TicketTag.tag),
            )
            .order_by(order_by)
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().unique().all()), total

    async def summary(
        self,
        *,
        visibility,
        user_id: UUID,
        include_queue: bool,
    ) -> dict[str, int | None]:
        closed = ("CLOSED", "CANCELLED", "REJECTED")

        async def _count(*clauses) -> int:
            query = select(Ticket.id)
            if visibility is not None:
                query = query.where(visibility)
            for clause in clauses:
                query = query.where(clause)
            return int(
                (
                    await self.session.execute(
                        select(func.count()).select_from(query.subquery())
                    )
                ).scalar_one()
            )

        result: dict[str, int | None] = {
            "my_tickets": await _count(Ticket.requester_id == user_id),
            "open_mine": await _count(
                Ticket.requester_id == user_id, Ticket.status.notin_(closed)
            ),
            "assigned_to_me": None,
            "unassigned": None,
        }
        if include_queue:
            result["assigned_to_me"] = await _count(
                Ticket.assigned_agent_id == user_id, Ticket.status.notin_(closed)
            )
            result["unassigned"] = await _count(
                Ticket.assigned_agent_id.is_(None), Ticket.status.notin_(closed)
            )
        return result

    async def add_status_history(self, row: TicketStatusHistory) -> None:
        self.session.add(row)
        await self.session.flush()

    async def add_assignment(self, row: TicketAssignment) -> None:
        self.session.add(row)
        await self.session.flush()

    async def list_status_history(self, ticket_id: UUID) -> list[TicketStatusHistory]:
        result = await self.session.execute(
            select(TicketStatusHistory)
            .options(selectinload(TicketStatusHistory.actor))
            .where(TicketStatusHistory.ticket_id == ticket_id)
            .order_by(TicketStatusHistory.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_assignments(self, ticket_id: UUID) -> list[TicketAssignment]:
        result = await self.session.execute(
            select(TicketAssignment)
            .options(selectinload(TicketAssignment.actor))
            .where(TicketAssignment.ticket_id == ticket_id)
            .order_by(TicketAssignment.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_or_create_tags(self, slugs: list[str]) -> list[Tag]:
        tags: list[Tag] = []
        for raw in slugs:
            slug = raw.strip().lower().replace(" ", "-")
            if not slug:
                continue
            result = await self.session.execute(select(Tag).where(Tag.slug == slug))
            tag = result.scalar_one_or_none()
            if tag is None:
                tag = Tag(slug=slug, name=slug)
                self.session.add(tag)
                await self.session.flush()
            tags.append(tag)
        return tags

    async def replace_tags(self, ticket: Ticket, tags: list[Tag]) -> None:
        await self.session.execute(delete(TicketTag).where(TicketTag.ticket_id == ticket.id))
        for tag in tags:
            self.session.add(TicketTag(ticket_id=ticket.id, tag_id=tag.id))
        await self.session.flush()
