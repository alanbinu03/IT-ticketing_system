from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    department_id: UUID
    description: str | None = None
    is_active: bool = True


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    department_id: UUID | None = None
    description: str | None = None
    is_active: bool | None = None


class TeamMemberCreate(BaseModel):
    user_id: UUID
    is_lead: bool = False


class TeamMemberOut(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    is_lead: bool


class DepartmentRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None
    department_id: UUID
    department: DepartmentRef | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: list[TeamMemberOut] | None = None
