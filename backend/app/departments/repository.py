from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.models import Department


class DepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, department_id: UUID) -> Department | None:
        return await self.session.get(Department, department_id)

    async def get_by_code(self, code: str) -> Department | None:
        result = await self.session.execute(
            select(Department).where(func.lower(Department.code) == code.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Department | None:
        result = await self.session.execute(
            select(Department).where(func.lower(Department.name) == name.lower())
        )
        return result.scalar_one_or_none()

    def _filters(self, stmt, *, is_active: bool | None, q: str | None):
        if is_active is not None:
            stmt = stmt.where(Department.is_active.is_(is_active))
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(Department.name.ilike(pattern) | Department.code.ilike(pattern))
        return stmt

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        is_active: bool | None = None,
        q: str | None = None,
    ) -> tuple[list[Department], int]:
        total = int(
            (
                await self.session.execute(
                    self._filters(select(func.count()).select_from(Department), is_active=is_active, q=q)
                )
            ).scalar_one()
        )
        rows = await self.session.execute(
            self._filters(select(Department), is_active=is_active, q=q)
            .order_by(Department.name)
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total

    async def add(self, department: Department) -> Department:
        self.session.add(department)
        await self.session.flush()
        return department
