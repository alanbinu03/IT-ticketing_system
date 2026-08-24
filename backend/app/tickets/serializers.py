from __future__ import annotations

from app.tickets.models import Ticket, TicketAssignment, TicketStatusHistory
from app.tickets.schemas import (
    AssignmentHistoryOut,
    NamedRef,
    StatusHistoryOut,
    TicketOut,
    UserRef,
)


def _user_ref(user) -> UserRef | None:
    if user is None:
        return None
    return UserRef(id=user.id, full_name=user.full_name, email=user.email)


def _named_ref(entity, *, code: str | None = None) -> NamedRef | None:
    if entity is None:
        return None
    return NamedRef(id=entity.id, name=entity.name, code=code or getattr(entity, "code", None))


def to_ticket_out(ticket: Ticket) -> TicketOut:
    tags = [link.tag.slug for link in ticket.tag_links if link.tag is not None]
    return TicketOut(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        requester=_user_ref(ticket.requester),
        department=_named_ref(ticket.department),
        assigned_team=_named_ref(ticket.assigned_team),
        assigned_agent=_user_ref(ticket.assigned_agent),
        category=_named_ref(ticket.category, code=None),
        subcategory=_named_ref(ticket.subcategory, code=None),
        priority=ticket.priority,
        severity=ticket.severity,
        status=ticket.status,
        source=ticket.source,
        assigned_at=ticket.assigned_at,
        first_response_at=ticket.first_response_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        due_at=ticket.due_at,
        resolution_summary=ticket.resolution_summary,
        tags=tags,
        version=ticket.version,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def to_status_history(row: TicketStatusHistory) -> StatusHistoryOut:
    return StatusHistoryOut(
        id=row.id,
        from_status=row.from_status,
        to_status=row.to_status,
        changed_by=_user_ref(row.actor),
        reason=row.reason,
        created_at=row.created_at,
    )


def to_assignment_history(row: TicketAssignment) -> AssignmentHistoryOut:
    return AssignmentHistoryOut(
        id=row.id,
        previous_team_id=row.previous_team_id,
        new_team_id=row.new_team_id,
        previous_agent_id=row.previous_agent_id,
        new_agent_id=row.new_agent_id,
        assigned_by=_user_ref(row.actor),
        created_at=row.created_at,
    )
