from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DepartmentRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str


class UserCreate(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    employee_code: str | None = Field(default=None, max_length=50)
    username: str | None = Field(default=None, max_length=80)
    department_id: UUID | None = None
    manager_id: UUID | None = None
    role_ids: list[UUID] = Field(default_factory=list)
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    employee_code: str | None = Field(default=None, max_length=50)
    username: str | None = Field(default=None, max_length=80)
    department_id: UUID | None = None
    manager_id: UUID | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRolesUpdate(BaseModel):
    role_ids: list[UUID]


class UserImportError(BaseModel):
    row: int
    email: str | None = None
    message: str


class UserImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[UserImportError] = Field(default_factory=list)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    employee_code: str | None
    username: str | None
    department_id: UUID | None
    department: DepartmentRef | None = None
    manager_id: UUID | None
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    roles: list[str] = Field(default_factory=list)


class UserMe(UserOut):
    permissions: list[str] = Field(default_factory=list)
    team_ids: list[UUID] = Field(default_factory=list)
