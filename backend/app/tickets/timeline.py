from __future__ import annotations

from app.comments.models import TicketComment
from app.tickets.models import TicketAssignment, TicketStatusHistory
from app.tickets.schemas import TimelineEventOut, UserRef


def _user_ref(user) -> UserRef | None:
    if user is None:
        return None
    return UserRef(id=user.id, full_name=user.full_name, email=user.email)


def build_timeline(
    status_history: list[TicketStatusHistory],
    assignments: list[TicketAssignment],
    comments: list[TicketComment],
) -> list[TimelineEventOut]:
    events: list[TimelineEventOut] = []
    for row in status_history:
        summary = (
            f"Status set to {row.to_status}"
            if row.from_status is None
            else f"Status changed from {row.from_status} to {row.to_status}"
        )
        events.append(
            TimelineEventOut(
                id=f"status:{row.id}",
                type="status",
                at=row.created_at,
                actor=_user_ref(row.actor),
                summary=summary,
                body=row.reason,
                metadata={"from_status": row.from_status, "to_status": row.to_status},
            )
        )
    for row in assignments:
        events.append(
            TimelineEventOut(
                id=f"assignment:{row.id}",
                type="assignment",
                at=row.created_at,
                actor=_user_ref(row.actor),
                summary="Assignment updated",
                metadata={
                    "previous_team_id": str(row.previous_team_id) if row.previous_team_id else None,
                    "new_team_id": str(row.new_team_id) if row.new_team_id else None,
                    "previous_agent_id": str(row.previous_agent_id)
                    if row.previous_agent_id
                    else None,
                    "new_agent_id": str(row.new_agent_id) if row.new_agent_id else None,
                },
            )
        )
    for row in comments:
        events.append(
            TimelineEventOut(
                id=f"comment:{row.id}",
                type="comment",
                at=row.created_at,
                actor=_user_ref(row.author),
                summary="Internal note" if row.type == "INTERNAL_NOTE" else "Comment",
                body=row.body,
                comment_type=row.type,
            )
        )
    events.sort(key=lambda item: item.at)
    return events
