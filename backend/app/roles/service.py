from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import invalidate_role_permission_cache
from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import ConflictError, NotFoundError
from app.roles.models import Permission, Role
from app.roles.repository import RoleRepository
from app.roles.schemas import RoleCreate, RoleUpdate


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RoleRepository(session)

    async def get(self, role_id: UUID) -> Role:
        role = await self.repo.get_by_id(role_id)
        if role is None:
            raise NotFoundError("Role not found.")
        return role

    async def list(self) -> list[Role]:
        return await self.repo.list_all()

    async def list_permissions(self) -> list[Permission]:
        return await self.repo.list_permissions()

    async def create(self, data: RoleCreate, actor_id: UUID) -> Role:
        if await self.repo.get_by_name(data.name.strip()):
            raise ConflictError("A role with this name already exists.")
        role = Role(name=data.name.strip(), description=data.description, is_system=False)
        await self.repo.add(role)
        if data.permission_ids:
            await self._set_permissions(role, data.permission_ids)
        enqueue_event(
            self.session,
            DomainEvent(
                name="role.changed",
                entity_type="role",
                entity_id=role.id,
                actor_id=actor_id,
                payload={"new": {"name": role.name, "permission_ids": [str(i) for i in data.permission_ids]}},
            ),
        )
        return await self.get(role.id)

    async def update(self, role_id: UUID, data: RoleUpdate, actor_id: UUID) -> Role:
        role = await self.get(role_id)
        previous = {"name": role.name}
        updates = data.model_dump(exclude_unset=True)
        if "name" in updates and updates["name"]:
            updates["name"] = updates["name"].strip()
            existing = await self.repo.get_by_name(updates["name"])
            if existing and existing.id != role.id:
                raise ConflictError("A role with this name already exists.")
        for field, value in updates.items():
            setattr(role, field, value)
        await self.session.flush()
        enqueue_event(
            self.session,
            DomainEvent(
                name="role.changed",
                entity_type="role",
                entity_id=role.id,
                actor_id=actor_id,
                payload={"previous": previous, "new": updates},
            ),
        )
        return await self.get(role.id)

    async def set_permissions(
        self, role_id: UUID, permission_ids: list[UUID], actor_id: UUID
    ) -> Role:
        role = await self.get(role_id)
        await self._set_permissions(role, permission_ids)
        await invalidate_role_permission_cache()
        enqueue_event(
            self.session,
            DomainEvent(
                name="role.changed",
                entity_type="role",
                entity_id=role.id,
                actor_id=actor_id,
                payload={"new": {"permission_ids": [str(i) for i in permission_ids]}},
            ),
        )
        return await self.get(role.id)

    async def _set_permissions(self, role: Role, permission_ids: list[UUID]) -> None:
        unique_ids = list(dict.fromkeys(permission_ids))
        found = await self.repo.get_permissions_by_ids(unique_ids)
        if len(found) != len(unique_ids):
            raise NotFoundError("One or more permissions were not found.")
        await self.repo.replace_permissions(role, unique_ids)
