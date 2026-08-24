from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.roles.models import Permission, Role, RolePermission, UserRole


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, role_id: UUID) -> Role | None:
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .order_by(Role.name)
        )
        return list(result.scalars().unique().all())

    async def add(self, role: Role) -> Role:
        self.session.add(role)
        await self.session.flush()
        return role

    async def get_roles_by_ids(self, role_ids: list[UUID]) -> list[Role]:
        if not role_ids:
            return []
        result = await self.session.execute(select(Role).where(Role.id.in_(role_ids)))
        return list(result.scalars().all())

    async def replace_permissions(self, role: Role, permission_ids: list[UUID]) -> None:
        await self.session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        for permission_id in permission_ids:
            self.session.add(RolePermission(role_id=role.id, permission_id=permission_id))
        await self.session.flush()

    async def list_permissions(self) -> list[Permission]:
        result = await self.session.execute(select(Permission).order_by(Permission.code))
        return list(result.scalars().all())

    async def get_permissions_by_ids(self, permission_ids: list[UUID]) -> list[Permission]:
        if not permission_ids:
            return []
        result = await self.session.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        return list(result.scalars().all())

    async def get_user_permission_codes(self, user_id: UUID) -> set[str]:
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def get_user_role_names(self, user_id: UUID) -> list[str]:
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
