from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.mixins import TimestampMixin
from app.database.base import Base

if TYPE_CHECKING:
    from app.departments.models import Department
    from app.roles.models import UserRole
    from app.teams.models import TeamMember


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_employee_code",
            "employee_code",
            unique=True,
            postgresql_where=text("employee_code IS NOT NULL"),
        ),
        Index(
            "uq_users_username",
            "username",
            unique=True,
            postgresql_where=text("username IS NOT NULL"),
        ),
        Index("ix_users_department_id", "department_id"),
        Index("ix_users_manager_id", "manager_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    employee_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def email_is_verified(self) -> bool:
        return self.email_verified_at is not None or self.is_verified

    department: Mapped[Department | None] = relationship(
        back_populates="users",
        foreign_keys=[department_id],
    )
    manager: Mapped[User | None] = relationship(
        remote_side="User.id",
        foreign_keys=[manager_id],
    )
    user_roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    team_memberships: Mapped[list[TeamMember]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
