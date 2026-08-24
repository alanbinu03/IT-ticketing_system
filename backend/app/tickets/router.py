from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, get_current_user, require_permission
from app.comments.schemas import CommentCreate, CommentOut
from app.comments.service import CommentService
from app.common.pagination import Page
from app.database.session import get_db
from app.tickets.enums import TicketPriority, TicketStatus
from app.tickets.schemas import (
    TicketAssignRequest,
    TicketCreate,
    TicketHistoryOut,
    TicketOut,
    TicketStatusRequest,
    TicketSummaryOut,
    TicketUpdate,
    TimelineEventOut,
    UserRef,
)
from app.tickets.serializers import to_assignment_history, to_status_history, to_ticket_out
from app.tickets.service import TicketService
from app.tickets.timeline import build_timeline

tickets_router = APIRouter(prefix="/tickets", tags=["tickets"])


def _comment_out(comment) -> CommentOut:
    author = None
    if comment.author is not None:
        author = UserRef(
            id=comment.author.id, full_name=comment.author.full_name, email=comment.author.email
        )
    return CommentOut(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author=author,
        body=comment.body,
        type=comment.type,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@tickets_router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    auth: AuthContext = Depends(require_permission("ticket.create")),
    session: AsyncSession = Depends(get_db),
) -> TicketOut:
    return to_ticket_out(await TicketService(session).create(payload, auth))


@tickets_router.get("", response_model=Page[TicketOut])
async def list_tickets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: list[TicketStatus] | None = Query(default=None, alias="status"),
    priority: list[TicketPriority] | None = Query(default=None),
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
    sort: Literal["created_at", "updated_at", "due_at", "priority"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Page[TicketOut]:
    items, total = await TicketService(session).list(
        auth,
        limit=limit,
        offset=offset,
        statuses=[item.value for item in status_filter] if status_filter else None,
        priorities=[item.value for item in priority] if priority else None,
        requester_id=requester_id,
        assigned_agent_id=assigned_agent_id,
        assigned_team_id=assigned_team_id,
        department_id=department_id,
        category_id=category_id,
        ticket_number=ticket_number,
        q=q,
        date_from=date_from,
        date_to=date_to,
        unassigned=unassigned,
        sort=sort,
        order=order,
    )
    return Page(
        items=[to_ticket_out(item) for item in items], total=total, limit=limit, offset=offset
    )


@tickets_router.get("/summary", response_model=TicketSummaryOut)
async def ticket_summary(
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TicketSummaryOut:
    return await TicketService(session).summary(auth)


@tickets_router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TicketOut:
    return to_ticket_out(await TicketService(session).get(ticket_id, auth))


@tickets_router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    auth: AuthContext = Depends(require_permission("ticket.update")),
    session: AsyncSession = Depends(get_db),
) -> TicketOut:
    return to_ticket_out(await TicketService(session).update(ticket_id, payload, auth))


@tickets_router.post("/{ticket_id}/assign", response_model=TicketOut)
async def assign_ticket(
    ticket_id: UUID,
    payload: TicketAssignRequest,
    auth: AuthContext = Depends(require_permission("ticket.assign", "ticket.reassign")),
    session: AsyncSession = Depends(get_db),
) -> TicketOut:
    return to_ticket_out(await TicketService(session).assign(ticket_id, payload, auth))


@tickets_router.post("/{ticket_id}/status", response_model=TicketOut)
async def change_ticket_status(
    ticket_id: UUID,
    payload: TicketStatusRequest,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TicketOut:
    return to_ticket_out(await TicketService(session).change_status(ticket_id, payload, auth))


@tickets_router.post(
    "/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED
)
async def add_comment(
    ticket_id: UUID,
    payload: CommentCreate,
    auth: AuthContext = Depends(require_permission("ticket.comment", "ticket.internal_note")),
    session: AsyncSession = Depends(get_db),
) -> CommentOut:
    return _comment_out(await CommentService(session).add(ticket_id, payload, auth))


@tickets_router.get("/{ticket_id}/comments", response_model=list[CommentOut])
async def list_comments(
    ticket_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CommentOut]:
    return [
        _comment_out(item)
        for item in await CommentService(session).list_for_ticket(ticket_id, auth)
    ]


@tickets_router.get("/{ticket_id}/history", response_model=TicketHistoryOut)
async def ticket_history(
    ticket_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TicketHistoryOut:
    status_rows, assignment_rows = await TicketService(session).history(ticket_id, auth)
    return TicketHistoryOut(
        status_history=[to_status_history(row) for row in status_rows],
        assignments=[to_assignment_history(row) for row in assignment_rows],
    )


@tickets_router.get("/{ticket_id}/timeline", response_model=list[TimelineEventOut])
async def ticket_timeline(
    ticket_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TimelineEventOut]:
    service = TicketService(session)
    status_rows, assignment_rows = await service.history(ticket_id, auth)
    comments = await CommentService(session).list_for_ticket(ticket_id, auth)
    return build_timeline(status_rows, assignment_rows, comments)
