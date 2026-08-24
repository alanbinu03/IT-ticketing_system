from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.categories.models import Category


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, category_id: UUID) -> Category | None:
        result = await self.session.execute(
            select(Category)
            .options(selectinload(Category.children))
            .where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, *, active_only: bool = False) -> list[Category]:
        stmt = select(Category).options(selectinload(Category.children)).order_by(Category.name)
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def add(self, category: Category) -> Category:
        self.session.add(category)
        await self.session.flush()
        return category
