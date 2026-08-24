from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import invalidate_user_permission_cache
from app.auth.repository import RefreshTokenRepository
from app.auth.security import hash_password
from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import ConflictError, NotFoundError
from app.departments.repository import DepartmentRepository
from app.roles.constants import ROLE_EMPLOYEE
from app.roles.repository import RoleRepository
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate


def _public_user_payload(user: User) -> dict:
    return {
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "department_id": str(user.department_id) if user.department_id else None,
    }


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)
        self.roles = RoleRepository(session)
        self.departments = DepartmentRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def get(self, user_id: UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None = None,
        department_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        return await self.repo.list(
            limit=limit,
            offset=offset,
            q=q,
            department_id=department_id,
            is_active=is_active,
        )

    async def create(self, data: UserCreate, actor_id: UUID) -> User:
        email = str(data.email).lower().strip()
        if await self.repo.get_by_email(email):
            raise ConflictError("A user with this email already exists.")
        if data.employee_code and await self.repo.get_by_employee_code(data.employee_code):
            raise ConflictError("A user with this employee code already exists.")
        if data.username and await self.repo.get_by_username(data.username):
            raise ConflictError("A user with this username already exists.")
        if data.department_id and await self.departments.get_by_id(data.department_id) is None:
            raise NotFoundError("Department not found.")
        if data.manager_id and await self.repo.get_by_id(data.manager_id) is None:
            raise NotFoundError("Manager not found.")

        user = User(
            email=email,
            password_hash=hash_password(data.password),
            full_name=data.full_name.strip(),
            employee_code=data.employee_code.strip() if data.employee_code else None,
            username=data.username.strip() if data.username else None,
            department_id=data.department_id,
            manager_id=data.manager_id,
            is_active=data.is_active,
            is_verified=True,
            email_verified_at=datetime.now(UTC),
        )
        await self.repo.add(user)
        await self._assign_roles(user, data.role_ids)
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.created",
                entity_type="user",
                entity_id=user.id,
                actor_id=actor_id,
                payload={"new": _public_user_payload(user)},
            ),
        )
        return await self.get(user.id)

    async def update(self, user_id: UUID, data: UserUpdate, actor_id: UUID) -> User:
        user = await self.get(user_id)
        previous = _public_user_payload(user)
        updates = data.model_dump(exclude_unset=True)
        if "password" in updates:
            password = updates.pop("password")
            if password:
                user.password_hash = hash_password(password)
        if "employee_code" in updates:
            code = updates["employee_code"]
            if code:
                existing = await self.repo.get_by_employee_code(code)
                if existing and existing.id != user.id:
                    raise ConflictError("A user with this employee code already exists.")
        if "username" in updates:
            username = updates["username"]
            if username:
                existing = await self.repo.get_by_username(username)
                if existing and existing.id != user.id:
                    raise ConflictError("A user with this username already exists.")
        if "department_id" in updates and updates["department_id"] is not None:
            if await self.departments.get_by_id(updates["department_id"]) is None:
                raise NotFoundError("Department not found.")
        if "manager_id" in updates and updates["manager_id"] is not None:
            if updates["manager_id"] == user.id:
                raise ConflictError("A user cannot be their own manager.")
            if await self.repo.get_by_id(updates["manager_id"]) is None:
                raise NotFoundError("Manager not found.")
        for field, value in updates.items():
            if field in {"full_name", "employee_code", "username"} and isinstance(value, str):
                value = value.strip() or None
            setattr(user, field, value)
        await self.session.flush()
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.updated",
                entity_type="user",
                entity_id=user.id,
                actor_id=actor_id,
                payload={"previous": previous, "new": _public_user_payload(user)},
            ),
        )
        return await self.get(user.id)

    async def disable(self, user_id: UUID, actor_id: UUID) -> User:
        if user_id == actor_id:
            raise ConflictError("You cannot disable your own account.", code="CANNOT_DISABLE_SELF")
        user = await self.get(user_id)
        if not user.is_active:
            return user
        previous = _public_user_payload(user)
        user.is_active = False
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await invalidate_user_permission_cache(user.id)
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.disabled",
                entity_type="user",
                entity_id=user.id,
                actor_id=actor_id,
                payload={"previous": previous, "new": _public_user_payload(user)},
            ),
        )
        return user

    async def set_roles(self, user_id: UUID, role_ids: list[UUID], actor_id: UUID) -> User:
        user = await self.get(user_id)
        previous_roles = [ur.role.name for ur in user.user_roles]
        await self._assign_roles(user, role_ids, allow_empty=False)
        await invalidate_user_permission_cache(user_id)
        await self.session.flush()
        self.session.expire(user)
        user = await self.get(user_id)
        new_roles = await self.roles.get_user_role_names(user_id)
        enqueue_event(
            self.session,
            DomainEvent(
                name="role.changed",
                entity_type="user",
                entity_id=user.id,
                actor_id=actor_id,
                payload={
                    "previous": {"roles": previous_roles},
                    "new": {"roles": new_roles},
                },
            ),
        )
        return user

    async def _assign_roles(
        self, user: User, role_ids: list[UUID], *, allow_empty: bool = True
    ) -> None:
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            employee = await self.roles.get_by_name(ROLE_EMPLOYEE)
            if employee is None:
                if not allow_empty:
                    raise NotFoundError("Employee role is not configured.")
                return
            await self.repo.set_roles(user, [employee])
            return
        found = await self.roles.get_roles_by_ids(unique_ids)
        if len(found) != len(unique_ids):
            raise NotFoundError("One or more roles were not found.")
        await self.repo.set_roles(user, found)
