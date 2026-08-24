from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, get_current_user
from app.database.session import get_db
from app.notifications.schemas import NotificationListOut, NotificationOut
from app.notifications.service import NotificationService

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("", response_model=NotificationListOut)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationListOut:
    items, total, unread = await NotificationService(session).list(
        auth.user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    return NotificationListOut(
        items=[NotificationOut.model_validate(item) for item in items],
        total=total,
        unread_count=unread,
        limit=limit,
        offset=offset,
    )


@notifications_router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await NotificationService(session).mark_all_read(auth.user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@notifications_router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationOut:
    item = await NotificationService(session).mark_read(notification_id, auth.user.id)
    return NotificationOut.model_validate(item)
