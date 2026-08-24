from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.sql import ColumnElement

from app.auth.dependencies import AuthContext
from app.common.exceptions import ForbiddenError
from app.tickets.models import Ticket


def viewer_team_ids(auth: AuthContext) -> list[UUID]:
    return [membership.team_id for membership in auth.user.team_memberships]


def can_view_ticket(auth: AuthContext, ticket: Ticket) -> bool:
    if auth.has("ticket.view_all"):
        return True
    if auth.has("ticket.view_own") and ticket.requester_id == auth.user.id:
        return True
    if auth.has("ticket.view_team"):
        if ticket.assigned_agent_id == auth.user.id:
            return True
        if ticket.assigned_team_id and ticket.assigned_team_id in viewer_team_ids(auth):
            return True
        if ticket.assigned_team_id is None and ticket.assigned_agent_id is None:
            return True
    return False


def ensure_can_view(auth: AuthContext, ticket: Ticket) -> None:
    if not can_view_ticket(auth, ticket):
        raise ForbiddenError("You do not have access to this ticket.")


def visibility_filter(auth: AuthContext) -> ColumnElement[bool] | None:
    if auth.has("ticket.view_all"):
        return None
    clauses: list[ColumnElement[bool]] = []
    if auth.has("ticket.view_own"):
        clauses.append(Ticket.requester_id == auth.user.id)
    if auth.has("ticket.view_team"):
        team_ids = viewer_team_ids(auth)
        unassigned = Ticket.assigned_team_id.is_(None) & Ticket.assigned_agent_id.is_(None)
        team_clause = (Ticket.assigned_agent_id == auth.user.id) | unassigned
        if team_ids:
            team_clause = team_clause | Ticket.assigned_team_id.in_(team_ids)
        clauses.append(team_clause)
    if not clauses:
        raise ForbiddenError()
    return or_(*clauses)
