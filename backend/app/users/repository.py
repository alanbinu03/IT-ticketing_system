from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.roles.models import Role, UserRole
from app.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_relations(self):
        return select(User).options(
            selectinload(User.department),
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.team_memberships),
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(self._with_relations().where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            self._with_relations().where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_employee_code(self, employee_code: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.employee_code == employee_code)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return result.scalar_one_or_none()

    def _filters(
        self,
        stmt,
        *,
        q: str | None,
        department_id: UUID | None,
        is_active: bool | None,
    ):
        if department_id is not None:
            stmt = stmt.where(User.department_id == department_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.employee_code.ilike(pattern),
                    User.username.ilike(pattern),
                )
            )
        return stmt

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None = None,
        department_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        total = int(
            (
                await self.session.execute(
                    self._filters(
                        select(func.count()).select_from(User),
                        q=q,
                        department_id=department_id,
                        is_active=is_active,
                    )
                )
            ).scalar_one()
        )
        rows = await self.session.execute(
            self._filters(
                self._with_relations(),
                q=q,
                department_id=department_id,
                is_active=is_active,
            )
            .order_by(User.full_name)
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().unique().all()), total

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_roles(self, user: User, roles: list[Role]) -> None:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        for role in roles:
            self.session.add(UserRole(user_id=user.id, role_id=role.id))
        await self.session.flush()
