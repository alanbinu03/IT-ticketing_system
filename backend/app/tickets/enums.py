from __future__ import annotations

from enum import StrEnum


class TicketStatus(StrEnum):
    NEW = "NEW"
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    WAITING_FOR_VENDOR = "WAITING_FOR_VENDOR"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    REOPENED = "REOPENED"


class TicketPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TicketSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TicketSource(StrEnum):
    WEB = "WEB"
    EMAIL = "EMAIL"
    API = "API"
    ADMIN = "ADMIN"
    MONITORING = "MONITORING"


class CommentType(StrEnum):
    PUBLIC_COMMENT = "PUBLIC_COMMENT"
    INTERNAL_NOTE = "INTERNAL_NOTE"


PRIORITY_RANK = {
    TicketPriority.CRITICAL: 1,
    TicketPriority.HIGH: 2,
    TicketPriority.MEDIUM: 3,
    TicketPriority.LOW: 4,
}

PRIORITY_LABELS = {
    TicketPriority.CRITICAL: "P1",
    TicketPriority.HIGH: "P2",
    TicketPriority.MEDIUM: "P3",
    TicketPriority.LOW: "P4",
}

STATUS_VALUES = tuple(status.value for status in TicketStatus)
PRIORITY_VALUES = tuple(priority.value for priority in TicketPriority)
SEVERITY_VALUES = tuple(severity.value for severity in TicketSeverity)
SOURCE_VALUES = tuple(source.value for source in TicketSource)
COMMENT_TYPE_VALUES = tuple(item.value for item in CommentType)
