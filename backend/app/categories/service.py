from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category
from app.categories.repository import CategoryRepository
from app.categories.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.common.exceptions import ConflictError, NotFoundError


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CategoryRepository(session)

    async def list_tree(self, *, active_only: bool = True) -> list[CategoryOut]:
        rows = await self.repo.list_all(active_only=active_only)
        by_id = {row.id: row for row in rows}
        children_map: dict[UUID | None, list[Category]] = {}
        for row in rows:
            children_map.setdefault(row.parent_id, []).append(row)

        def to_out(row: Category) -> CategoryOut:
            kids = [to_out(child) for child in children_map.get(row.id, []) if child.id in by_id]
            kids.sort(key=lambda item: item.name)
            return CategoryOut(
                id=row.id,
                name=row.name,
                parent_id=row.parent_id,
                is_active=row.is_active,
                description=row.description,
                children=kids,
            )

        roots = [to_out(row) for row in children_map.get(None, []) if row.id in by_id]
        roots.sort(key=lambda item: item.name)
        return roots

    async def create(self, data: CategoryCreate) -> CategoryOut:
        if data.parent_id:
            parent = await self.repo.get_by_id(data.parent_id)
            if parent is None:
                raise NotFoundError("Parent category not found.")
            if parent.parent_id is not None:
                raise ConflictError("Only one level of subcategory is supported.")
        category = Category(
            name=data.name.strip(),
            parent_id=data.parent_id,
            description=data.description,
            is_active=data.is_active,
        )
        await self.repo.add(category)
        loaded = await self.repo.get_by_id(category.id)
        assert loaded is not None
        return CategoryOut(
            id=loaded.id,
            name=loaded.name,
            parent_id=loaded.parent_id,
            is_active=loaded.is_active,
            description=loaded.description,
            children=[],
        )

    async def update(self, category_id: UUID, data: CategoryUpdate) -> CategoryOut:
        category = await self.repo.get_by_id(category_id)
        if category is None:
            raise NotFoundError("Category not found.")
        updates = data.model_dump(exclude_unset=True)
        if "name" in updates and updates["name"]:
            updates["name"] = updates["name"].strip()
        for field, value in updates.items():
            setattr(category, field, value)
        await self.session.flush()
        loaded = await self.repo.get_by_id(category.id)
        assert loaded is not None
        return CategoryOut(
            id=loaded.id,
            name=loaded.name,
            parent_id=loaded.parent_id,
            is_active=loaded.is_active,
            description=loaded.description,
            children=[],
        )
