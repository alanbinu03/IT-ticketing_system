from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.tickets.enums import CommentType
from app.tickets.schemas import UserRef


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    type: CommentType = CommentType.PUBLIC_COMMENT


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    author: UserRef | None = None
    body: str
    type: CommentType
    is_edited: bool
    created_at: datetime
    updated_at: datetime
