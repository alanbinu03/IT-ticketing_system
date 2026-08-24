from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.contextvars import bind_contextvars

from app.auth.rbac import cache_user_permissions, load_cached_permissions
from app.auth.security import decode_access_token
from app.common.exceptions import ForbiddenError, UnauthorizedError
from app.database.session import get_db
from app.roles.repository import RoleRepository
from app.users.models import User
from app.users.repository import UserRepository

_bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthContext:
    user: User
    permissions: set[str]
    roles: list[str]

    def has(self, permission: str) -> bool:
        return permission in self.permissions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired access token.")
    if not user.is_active:
        raise UnauthorizedError("This account has been disabled.", code="ACCOUNT_DISABLED")

    cached = await load_cached_permissions(user.id)
    if cached is None:
        cached = await RoleRepository(session).get_user_permission_codes(user.id)
        await cache_user_permissions(user.id, cached)

    roles = [ur.role.name for ur in user.user_roles]
    bind_contextvars(user_id=str(user.id))
    return AuthContext(user=user, permissions=cached, roles=roles)


def require_permission(*codes: str):
    async def _checker(auth: AuthContext = Depends(get_current_user)) -> AuthContext:
        if not any(auth.has(code) for code in codes):
            raise ForbiddenError()
        return auth

    return _checker
