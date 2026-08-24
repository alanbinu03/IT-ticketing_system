"""Centralized ticket status transition rules. Replaceable later with stored workflow config."""

from __future__ import annotations

from app.common.exceptions import ConflictError
from app.tickets.enums import TicketStatus

ALLOWED_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    TicketStatus.NEW: frozenset(
        {
            TicketStatus.OPEN,
            TicketStatus.ASSIGNED,
            TicketStatus.CANCELLED,
            TicketStatus.REJECTED,
        }
    ),
    TicketStatus.OPEN: frozenset(
        {
            TicketStatus.ASSIGNED,
            TicketStatus.IN_PROGRESS,
            TicketStatus.CANCELLED,
            TicketStatus.REJECTED,
        }
    ),
    TicketStatus.ASSIGNED: frozenset(
        {
            TicketStatus.IN_PROGRESS,
            TicketStatus.OPEN,
            TicketStatus.CANCELLED,
        }
    ),
    TicketStatus.IN_PROGRESS: frozenset(
        {
            TicketStatus.WAITING_FOR_USER,
            TicketStatus.WAITING_FOR_VENDOR,
            TicketStatus.ON_HOLD,
            TicketStatus.RESOLVED,
        }
    ),
    TicketStatus.WAITING_FOR_USER: frozenset(
        {
            TicketStatus.IN_PROGRESS,
            TicketStatus.ON_HOLD,
            TicketStatus.RESOLVED,
        }
    ),
    TicketStatus.WAITING_FOR_VENDOR: frozenset(
        {
            TicketStatus.IN_PROGRESS,
            TicketStatus.ON_HOLD,
        }
    ),
    TicketStatus.ON_HOLD: frozenset({TicketStatus.IN_PROGRESS}),
    TicketStatus.RESOLVED: frozenset({TicketStatus.CLOSED, TicketStatus.REOPENED}),
    TicketStatus.REOPENED: frozenset({TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS}),
    TicketStatus.CLOSED: frozenset(),
    TicketStatus.CANCELLED: frozenset(),
    TicketStatus.REJECTED: frozenset(),
}


class WorkflowService:
    def can_transition(self, current: TicketStatus, target: TicketStatus) -> bool:
        return target in ALLOWED_TRANSITIONS.get(current, frozenset())

    def assert_can_transition(self, current: TicketStatus, target: TicketStatus) -> None:
        if current == target:
            return
        if not self.can_transition(current, target):
            raise ConflictError(
                f"Ticket cannot move from {current.value} to {target.value}.",
                code="INVALID_STATUS_TRANSITION",
            )

    def assignment_status(self, current: TicketStatus) -> TicketStatus | None:
        """Status to apply when a ticket is assigned, if a transition is required."""
        if current in {TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.REOPENED}:
            return TicketStatus.ASSIGNED
        return None
