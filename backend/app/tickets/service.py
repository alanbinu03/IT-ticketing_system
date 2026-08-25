from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext
from app.categories.models import Category
from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.departments.models import Department
from app.teams.models import Team
from app.tickets.access import ensure_can_view, visibility_filter
from app.tickets.enums import TicketStatus
from app.tickets.models import Ticket, TicketAssignment, TicketStatusHistory
from app.tickets.repository import TicketRepository
from app.tickets.schemas import (
    TicketAssignRequest,
    TicketCreate,
    TicketStatusRequest,
    TicketSummaryOut,
    TicketUpdate,
)
from app.users.models import User
from app.workflows.service import WorkflowService


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TicketRepository(session)
        self.workflow = WorkflowService()

    async def get(self, ticket_id: UUID, auth: AuthContext) -> Ticket:
        ticket = await self.repo.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        ensure_can_view(auth, ticket)
        return ticket

    async def list(self, auth: AuthContext, **kwargs) -> tuple[list[Ticket], int]:
        return await self.repo.list(visibility=visibility_filter(auth), **kwargs)

    async def summary(self, auth: AuthContext) -> TicketSummaryOut:
        data = await self.repo.summary(
            visibility=visibility_filter(auth),
            user_id=auth.user.id,
            include_queue=auth.has("ticket.view_all"),
        )
        return TicketSummaryOut.model_validate(data)

    async def create(self, data: TicketCreate, auth: AuthContext) -> Ticket:
        if not auth.has("ticket.create"):
            raise ForbiddenError()
        department_id = auth.user.department_id
        if department_id is None:
            raise ConflictError("Your account must belong to a department before opening a ticket.")
        if await self.session.get(Department, department_id) is None:
            raise NotFoundError("Department not found.")
        await self._validate_category(data.category_id, data.subcategory_id)
        if data.assigned_team_id or data.assigned_agent_id:
            if not auth.has("ticket.assign"):
                raise ForbiddenError("You cannot assign a ticket during creation.")
            await self._validate_assignees(data.assigned_team_id, data.assigned_agent_id)

        year = datetime.now(UTC).year
        number = await self.repo.allocate_ticket_number(year)
        now = datetime.now(UTC)
        status = TicketStatus.NEW
        assigned_at = None
        if data.assigned_team_id or data.assigned_agent_id:
            nxt = self.workflow.assignment_status(status)
            if nxt:
                self.workflow.assert_can_transition(status, nxt)
                status = nxt
            assigned_at = now

        ticket = Ticket(
            ticket_number=number,
            title=data.title.strip(),
            description=data.description.strip(),
            requester_id=auth.user.id,
            department_id=department_id,
            assigned_team_id=data.assigned_team_id,
            assigned_agent_id=data.assigned_agent_id,
            category_id=data.category_id,
            subcategory_id=data.subcategory_id,
            priority=data.priority.value,
            severity=data.severity.value,
            status=status.value,
            source=data.source.value,
            assigned_at=assigned_at,
            created_by=auth.user.id,
            updated_by=auth.user.id,
            version=1,
        )
        await self.repo.add(ticket)
        await self.repo.add_status_history(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=None,
                to_status=status.value,
                changed_by=auth.user.id,
                reason="Ticket created",
            )
        )
        if data.assigned_team_id or data.assigned_agent_id:
            await self.repo.add_assignment(
                TicketAssignment(
                    ticket_id=ticket.id,
                    previous_team_id=None,
                    new_team_id=data.assigned_team_id,
                    previous_agent_id=None,
                    new_agent_id=data.assigned_agent_id,
                    assigned_by=auth.user.id,
                )
            )
        if data.tags:
            tags = await self.repo.get_or_create_tags(data.tags)
            await self.repo.replace_tags(ticket, tags)
        enqueue_event(
            self.session,
            DomainEvent(
                name="ticket.created",
                entity_type="ticket",
                entity_id=ticket.id,
                actor_id=auth.user.id,
                payload={
                    "new": {
                        "ticket_number": number,
                        "title": ticket.title,
                        "status": status.value,
                        "priority": data.priority.value,
                        "category": getattr(await self.session.get(Category, data.category_id), "name", None)
                        if data.category_id
                        else None,
                        "created": now.strftime("%d %B %Y, %H:%M"),
                        "requester_id": str(auth.user.id),
                        "requester_name": auth.user.full_name,
                        "requester_email": auth.user.email,
                    }
                },
            ),
        )
        if data.assigned_team_id or data.assigned_agent_id:
            enqueue_event(
                self.session,
                DomainEvent(
                    name="ticket.assigned",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    actor_id=auth.user.id,
                    payload={
                        "new": {
                            "team_id": str(data.assigned_team_id) if data.assigned_team_id else None
                        }
                    },
                ),
            )
        return await self._reload(ticket.id)

    async def update(self, ticket_id: UUID, data: TicketUpdate, auth: AuthContext) -> Ticket:
        ticket = await self._lock(ticket_id, auth, data.version)
        if not auth.has("ticket.update"):
            raise ForbiddenError()
        previous = {"title": ticket.title, "priority": ticket.priority, "status": ticket.status}
        updates = data.model_dump(exclude_unset=True, exclude={"version", "tags"})
        if "priority" in updates:
            if not auth.has("ticket.change_priority"):
                raise ForbiddenError()
            updates["priority"] = data.priority.value if data.priority else ticket.priority
        if "severity" in updates and data.severity:
            updates["severity"] = data.severity.value
        if "category_id" in updates or "subcategory_id" in updates:
            await self._validate_category(
                updates.get("category_id", ticket.category_id),
                updates.get("subcategory_id", ticket.subcategory_id),
            )
        for field, value in updates.items():
            if field in {"title", "description"} and isinstance(value, str):
                value = value.strip()
            setattr(ticket, field, value)
        if data.tags is not None:
            tags = await self.repo.get_or_create_tags(data.tags)
            await self.repo.replace_tags(ticket, tags)
        ticket.updated_by = auth.user.id
        ticket.version += 1
        await self.session.flush()
        enqueue_event(
            self.session,
            DomainEvent(
                name="ticket.updated",
                entity_type="ticket",
                entity_id=ticket.id,
                actor_id=auth.user.id,
                payload={
                    "previous": previous,
                    "new": {"title": ticket.title, "priority": ticket.priority},
                },
            ),
        )
        if "priority" in updates and previous["priority"] != ticket.priority:
            enqueue_event(
                self.session,
                DomainEvent(
                    name="ticket.priority_changed",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    actor_id=auth.user.id,
                    payload={
                        "previous": {"priority": previous["priority"]},
                        "new": {"priority": ticket.priority},
                    },
                ),
            )
        return await self._reload(ticket.id)

    async def assign(self, ticket_id: UUID, data: TicketAssignRequest, auth: AuthContext) -> Ticket:
        ticket = await self._lock(ticket_id, auth, data.version)
        currently_assigned = (
            ticket.assigned_team_id is not None or ticket.assigned_agent_id is not None
        )
        needed = "ticket.reassign" if currently_assigned else "ticket.assign"
        if not auth.has(needed):
            raise ForbiddenError()
        releasing = data.agent_id is None and data.team_id is None
        if releasing:
            if not currently_assigned:
                return ticket
            current = TicketStatus(ticket.status)
            if current in {
                TicketStatus.RESOLVED,
                TicketStatus.CLOSED,
                TicketStatus.CANCELLED,
                TicketStatus.REJECTED,
            }:
                raise ConflictError("This ticket can no longer be released.")
        else:
            await self._validate_assignees(data.team_id, data.agent_id)
            if data.agent_id is None:
                raise ConflictError("Select an admin to assign this ticket to.")
        previous_team, previous_agent = ticket.assigned_team_id, ticket.assigned_agent_id
        if previous_team == data.team_id and previous_agent == data.agent_id:
            return ticket
        now = datetime.now(UTC)
        ticket.assigned_team_id = data.team_id
        ticket.assigned_agent_id = data.agent_id
        if releasing:
            ticket.assigned_at = None
        elif ticket.assigned_at is None:
            ticket.assigned_at = now
        current = TicketStatus(ticket.status)
        nxt = (
            self.workflow.unassignment_status(current)
            if releasing
            else self.workflow.assignment_status(current)
        )
        if nxt and nxt != current:
            await self._apply_status(
                ticket,
                nxt,
                auth.user.id,
                reason="Returned to unassigned" if releasing else "Assigned",
            )
        ticket.updated_by = auth.user.id
        ticket.version += 1
        await self.repo.add_assignment(
            TicketAssignment(
                ticket_id=ticket.id,
                previous_team_id=previous_team,
                new_team_id=data.team_id,
                previous_agent_id=previous_agent,
                new_agent_id=data.agent_id,
                assigned_by=auth.user.id,
            )
        )
        enqueue_event(
            self.session,
            DomainEvent(
                name="ticket.unassigned" if releasing else "ticket.assigned",
                entity_type="ticket",
                entity_id=ticket.id,
                actor_id=auth.user.id,
                payload={
                    "previous": {"team_id": str(previous_team) if previous_team else None},
                    "new": {
                        "team_id": str(data.team_id) if data.team_id else None,
                        "agent_id": str(data.agent_id) if data.agent_id else None,
                    },
                },
            ),
        )
        await self.session.flush()
        return await self._reload(ticket.id)

    async def change_status(
        self, ticket_id: UUID, data: TicketStatusRequest, auth: AuthContext
    ) -> Ticket:
        ticket = await self._lock(ticket_id, auth, data.version)
        target = data.status
        current = TicketStatus(ticket.status)
        self.workflow.assert_can_transition(current, target)
        required = {
            TicketStatus.RESOLVED: "ticket.resolve",
            TicketStatus.CLOSED: "ticket.close",
            TicketStatus.REOPENED: "ticket.reopen",
        }.get(target, "ticket.update")
        if current in {TicketStatus.RESOLVED, TicketStatus.CLOSED} and target in {
            TicketStatus.IN_PROGRESS,
            TicketStatus.REOPENED,
        }:
            required = "ticket.reopen"
        if not auth.has(required):
            raise ForbiddenError()
        await self._apply_status(
            ticket,
            target,
            auth.user.id,
            reason=data.reason,
            resolution_summary=data.resolution_summary,
        )
        ticket.updated_by = auth.user.id
        ticket.version += 1
        await self.session.flush()
        return await self._reload(ticket.id)

    async def history(
        self, ticket_id: UUID, auth: AuthContext
    ) -> tuple[list[TicketStatusHistory], list[TicketAssignment]]:
        await self.get(ticket_id, auth)
        return await self.repo.list_status_history(ticket_id), await self.repo.list_assignments(
            ticket_id
        )

    async def _reload(self, ticket_id: UUID) -> Ticket:
        cached = await self.session.get(Ticket, ticket_id)
        if cached is not None:
            self.session.expire(cached)
        loaded = await self.repo.get_by_id(ticket_id)
        if loaded is None:
            raise NotFoundError("Ticket not found.")
        return loaded

    async def _lock(self, ticket_id: UUID, auth: AuthContext, version: int | None) -> Ticket:
        ticket = await self.repo.get_for_update(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        ensure_can_view(auth, ticket)
        if version is not None and ticket.version != version:
            raise ConflictError(
                "Ticket was updated by another user. Reload and retry.", code="CONCURRENT_UPDATE"
            )
        return ticket

    async def _apply_status(
        self,
        ticket: Ticket,
        target: TicketStatus,
        actor_id: UUID,
        *,
        reason: str | None = None,
        resolution_summary: str | None = None,
    ) -> None:
        current = TicketStatus(ticket.status)
        if current == target:
            return
        now = datetime.now(UTC)
        ticket.status = target.value
        if target == TicketStatus.RESOLVED:
            ticket.resolved_at = now
            if resolution_summary:
                ticket.resolution_summary = resolution_summary.strip()
        if target == TicketStatus.CLOSED:
            ticket.closed_at = now
        if target == TicketStatus.REOPENED or (
            target == TicketStatus.IN_PROGRESS
            and current in {TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.REOPENED}
        ):
            ticket.resolved_at = None
            ticket.closed_at = None
        await self.repo.add_status_history(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=current.value,
                to_status=target.value,
                changed_by=actor_id,
                reason=reason,
            )
        )
        event_name = "ticket.status_changed"
        if target == TicketStatus.RESOLVED:
            event_name = "ticket.resolved"
        elif target == TicketStatus.CLOSED:
            event_name = "ticket.closed"
        elif target == TicketStatus.REOPENED:
            event_name = "ticket.reopened"
        enqueue_event(
            self.session,
            DomainEvent(
                name=event_name,
                entity_type="ticket",
                entity_id=ticket.id,
                actor_id=actor_id,
                payload={
                    "previous": {"status": current.value},
                    "new": {"status": target.value},
                    "reason": reason,
                },
            ),
        )
        if event_name != "ticket.status_changed":
            enqueue_event(
                self.session,
                DomainEvent(
                    name="ticket.status_changed",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    actor_id=actor_id,
                    payload={
                        "previous": {"status": current.value},
                        "new": {"status": target.value},
                    },
                ),
            )

    async def _validate_category(
        self, category_id: UUID | None, subcategory_id: UUID | None
    ) -> None:
        category = None
        if category_id:
            category = await self.session.get(Category, category_id)
            if category is None or not category.is_active:
                raise NotFoundError("Category not found.")
            if category.parent_id is not None:
                raise ConflictError("category_id must be a top-level category.")
        if subcategory_id:
            sub = await self.session.get(Category, subcategory_id)
            if sub is None or not sub.is_active:
                raise NotFoundError("Subcategory not found.")
            if category_id and sub.parent_id != category_id:
                raise ConflictError("Subcategory does not belong to the selected category.")
            if not category_id and sub.parent_id is None:
                raise ConflictError("subcategory_id must reference a child category.")

    async def _validate_assignees(self, team_id: UUID | None, agent_id: UUID | None) -> None:
        if team_id and await self.session.get(Team, team_id) is None:
            raise NotFoundError("Team not found.")
        if agent_id:
            agent = await self.session.get(User, agent_id)
            if agent is None or not agent.is_active:
                raise NotFoundError("Agent not found.")
