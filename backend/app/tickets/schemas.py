from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.tickets.enums import TicketPriority, TicketSeverity, TicketSource, TicketStatus


class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str


class NamedRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None = None


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    severity: TicketSeverity = TicketSeverity.MEDIUM
    source: TicketSource = TicketSource.WEB
    assigned_team_id: UUID | None = None
    assigned_agent_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=3)
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    priority: TicketPriority | None = None
    severity: TicketSeverity | None = None
    tags: list[str] | None = None
    version: int | None = None


class TicketAssignRequest(BaseModel):
    team_id: UUID | None = None
    agent_id: UUID | None = None
    version: int | None = None


class TicketStatusRequest(BaseModel):
    status: TicketStatus
    reason: str | None = Field(default=None, max_length=2000)
    resolution_summary: str | None = Field(default=None, max_length=4000)
    version: int | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_number: str
    title: str
    description: str
    requester: UserRef | None = None
    department: NamedRef | None = None
    assigned_team: NamedRef | None = None
    assigned_agent: UserRef | None = None
    category: NamedRef | None = None
    subcategory: NamedRef | None = None
    priority: TicketPriority
    severity: TicketSeverity
    status: TicketStatus
    source: TicketSource
    assigned_at: datetime | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    due_at: datetime | None
    resolution_summary: str | None
    tags: list[str] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime


class StatusHistoryOut(BaseModel):
    id: UUID
    from_status: TicketStatus | None
    to_status: TicketStatus
    changed_by: UserRef | None = None
    reason: str | None
    created_at: datetime


class AssignmentHistoryOut(BaseModel):
    id: UUID
    previous_team_id: UUID | None
    new_team_id: UUID | None
    previous_agent_id: UUID | None
    new_agent_id: UUID | None
    assigned_by: UserRef | None = None
    created_at: datetime


class TicketHistoryOut(BaseModel):
    status_history: list[StatusHistoryOut]
    assignments: list[AssignmentHistoryOut]


class TimelineEventOut(BaseModel):
    id: str
    type: str
    at: datetime
    actor: UserRef | None = None
    summary: str
    body: str | None = None
    comment_type: str | None = None
    metadata: dict | None = None


class TicketSummaryOut(BaseModel):
    my_tickets: int
    open_mine: int
    assigned_to_me: int | None = None
    unassigned: int | None = None
