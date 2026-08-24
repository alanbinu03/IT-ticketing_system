from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import ConflictError, NotFoundError
from app.departments.models import Department
from app.departments.repository import DepartmentRepository
from app.departments.schemas import DepartmentCreate, DepartmentUpdate


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DepartmentRepository(session)

    async def get(self, department_id: UUID) -> Department:
        department = await self.repo.get_by_id(department_id)
        if department is None:
            raise NotFoundError("Department not found.")
        return department

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        is_active: bool | None = None,
        q: str | None = None,
    ) -> tuple[list[Department], int]:
        return await self.repo.list(limit=limit, offset=offset, is_active=is_active, q=q)

    async def create(self, data: DepartmentCreate, actor_id: UUID) -> Department:
        if await self.repo.get_by_code(data.code) or await self.repo.get_by_name(data.name):
            raise ConflictError("A department with this name or code already exists.")
        department = Department(
            name=data.name.strip(),
            code=data.code.strip().upper(),
            description=data.description,
            is_active=data.is_active,
        )
        await self.repo.add(department)
        enqueue_event(
            self.session,
            DomainEvent(
                name="department.created",
                entity_type="department",
                entity_id=department.id,
                actor_id=actor_id,
                payload={"new": {"name": department.name, "code": department.code}},
            ),
        )
        return department

    async def update(
        self, department_id: UUID, data: DepartmentUpdate, actor_id: UUID
    ) -> Department:
        department = await self.get(department_id)
        previous = {"name": department.name, "code": department.code, "is_active": department.is_active}
        updates = data.model_dump(exclude_unset=True)
        if "code" in updates and updates["code"]:
            updates["code"] = updates["code"].strip().upper()
            existing = await self.repo.get_by_code(updates["code"])
            if existing and existing.id != department.id:
                raise ConflictError("A department with this code already exists.")
        if "name" in updates and updates["name"]:
            updates["name"] = updates["name"].strip()
            existing = await self.repo.get_by_name(updates["name"])
            if existing and existing.id != department.id:
                raise ConflictError("A department with this name already exists.")
        for field, value in updates.items():
            setattr(department, field, value)
        await self.session.flush()
        enqueue_event(
            self.session,
            DomainEvent(
                name="department.updated",
                entity_type="department",
                entity_id=department.id,
                actor_id=actor_id,
                payload={"previous": previous, "new": updates},
            ),
        )
        return department
