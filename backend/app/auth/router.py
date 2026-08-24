from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, get_current_user, require_permission
from app.auth.schemas import (
    AllowedDomainsResponse,
    CompleteRegistrationRequest,
    CompleteRegistrationResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RequestOtpRequest,
    RequestOtpResponse,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.config import get_settings
from app.auth.service import AuthService
from app.common.pagination import Page
from app.database.session import get_db
from app.departments.schemas import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.departments.service import DepartmentService
from app.roles.models import Role
from app.roles.schemas import (
    PermissionOut,
    RoleCreate,
    RoleOut,
    RolePermissionsUpdate,
    RoleUpdate,
)
from app.roles.service import RoleService
from app.teams.schemas import TeamCreate, TeamMemberCreate, TeamOut, TeamUpdate
from app.teams.service import TeamService
from app.users.schemas import UserCreate, UserMe, UserOut, UserRolesUpdate, UserUpdate
from app.users.serializers import to_team_out, to_user_out
from app.users.service import UserService


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def to_role_out(role: Role) -> RoleOut:
    permissions = [
        PermissionOut.model_validate(link.permission)
        for link in role.role_permissions
        if link.permission is not None
    ]
    permissions.sort(key=lambda item: item.code)
    return RoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permissions=permissions,
    )


auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    service = AuthService(session)
    access, refresh, expires_in, user = await service.login(
        payload.email,
        payload.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        user=user,
    )


@auth_router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    service = AuthService(session)
    access, refresh, expires_in, user = await service.admin_login(
        payload.email,
        payload.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        user=user,
    )


@auth_router.get("/register/allowed-domains", response_model=AllowedDomainsResponse)
async def registration_allowed_domains() -> AllowedDomainsResponse:
    return AllowedDomainsResponse(domains=get_settings().allowed_email_domain_list)


@auth_router.post("/register/request-otp", response_model=RequestOtpResponse)
async def request_registration_otp(
    payload: RequestOtpRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> RequestOtpResponse:
    message = await AuthService(session).request_registration_otp(
        str(payload.email),
        ip_address=_client_ip(request),
    )
    return RequestOtpResponse(message=message)


@auth_router.post("/register/verify-otp", response_model=VerifyOtpResponse)
async def verify_registration_otp(
    payload: VerifyOtpRequest,
    session: AsyncSession = Depends(get_db),
) -> VerifyOtpResponse:
    token = await AuthService(session).verify_registration_otp(str(payload.email), payload.otp)
    return VerifyOtpResponse(registration_token=token)


@auth_router.post("/register/complete", response_model=CompleteRegistrationResponse)
async def complete_registration(
    payload: CompleteRegistrationRequest,
    session: AsyncSession = Depends(get_db),
) -> CompleteRegistrationResponse:
    await AuthService(session).complete_registration(
        payload.registration_token,
        payload.full_name,
        payload.password,
    )
    return CompleteRegistrationResponse(message="Account created successfully")


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    service = AuthService(session)
    access, refresh_token, expires_in, user = await service.refresh(
        payload.refresh_token,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=user,
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db),
) -> Response:
    await AuthService(session).logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/me", response_model=UserMe)
async def read_me(
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserMe:
    return await AuthService(session).build_user_me(auth.user)


@users_router.get("", response_model=Page[UserOut])
async def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    department_id: UUID | None = None,
    is_active: bool | None = None,
    _auth: AuthContext = Depends(require_permission("user.view")),
    session: AsyncSession = Depends(get_db),
) -> Page[UserOut]:
    items, total = await UserService(session).list(
        limit=limit, offset=offset, q=q, department_id=department_id, is_active=is_active
    )
    return Page(
        items=[to_user_out(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@users_router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    auth: AuthContext = Depends(require_permission("user.create")),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await UserService(session).create(payload, actor_id=auth.user.id)
    return to_user_out(user)


@users_router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    if user_id != auth.user.id and not auth.has("user.view"):
        from app.common.exceptions import ForbiddenError

        raise ForbiddenError()
    return to_user_out(await UserService(session).get(user_id))


@users_router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    auth: AuthContext = Depends(require_permission("user.update")),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    return to_user_out(await UserService(session).update(user_id, payload, actor_id=auth.user.id))


@users_router.post("/{user_id}/disable", response_model=UserOut)
async def disable_user(
    user_id: UUID,
    auth: AuthContext = Depends(require_permission("user.disable")),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    return to_user_out(await UserService(session).disable(user_id, actor_id=auth.user.id))


@users_router.put("/{user_id}/roles", response_model=UserOut)
async def set_user_roles(
    user_id: UUID,
    payload: UserRolesUpdate,
    auth: AuthContext = Depends(require_permission("role.manage")),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    return to_user_out(
        await UserService(session).set_roles(user_id, payload.role_ids, actor_id=auth.user.id)
    )


roles_router = APIRouter(prefix="/roles", tags=["roles"])


@roles_router.get("", response_model=list[RoleOut])
async def list_roles(
    _auth: AuthContext = Depends(require_permission("role.manage", "user.view", "user.create")),
    session: AsyncSession = Depends(get_db),
) -> list[RoleOut]:
    return [to_role_out(role) for role in await RoleService(session).list()]


@roles_router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    auth: AuthContext = Depends(require_permission("role.manage")),
    session: AsyncSession = Depends(get_db),
) -> RoleOut:
    return to_role_out(await RoleService(session).create(payload, actor_id=auth.user.id))


@roles_router.get("/{role_id}", response_model=RoleOut)
async def get_role(
    role_id: UUID,
    _auth: AuthContext = Depends(require_permission("role.manage")),
    session: AsyncSession = Depends(get_db),
) -> RoleOut:
    return to_role_out(await RoleService(session).get(role_id))


@roles_router.patch("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    auth: AuthContext = Depends(require_permission("role.manage")),
    session: AsyncSession = Depends(get_db),
) -> RoleOut:
    return to_role_out(await RoleService(session).update(role_id, payload, actor_id=auth.user.id))


@roles_router.put("/{role_id}/permissions", response_model=RoleOut)
async def set_role_permissions(
    role_id: UUID,
    payload: RolePermissionsUpdate,
    auth: AuthContext = Depends(require_permission("role.manage")),
    session: AsyncSession = Depends(get_db),
) -> RoleOut:
    return to_role_out(
        await RoleService(session).set_permissions(
            role_id, payload.permission_ids, actor_id=auth.user.id
        )
    )


permissions_router = APIRouter(prefix="/permissions", tags=["roles"])


@permissions_router.get("", response_model=list[PermissionOut])
async def list_permissions(
    _auth: AuthContext = Depends(require_permission("role.manage")),
    session: AsyncSession = Depends(get_db),
) -> list[PermissionOut]:
    return [
        PermissionOut.model_validate(item) for item in await RoleService(session).list_permissions()
    ]


departments_router = APIRouter(prefix="/departments", tags=["departments"])


@departments_router.get("", response_model=Page[DepartmentOut])
async def list_departments(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    is_active: bool | None = None,
    _auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Page[DepartmentOut]:
    items, total = await DepartmentService(session).list(
        limit=limit, offset=offset, is_active=is_active, q=q
    )
    return Page(
        items=[DepartmentOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@departments_router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    auth: AuthContext = Depends(require_permission("department.manage")),
    session: AsyncSession = Depends(get_db),
) -> DepartmentOut:
    dept = await DepartmentService(session).create(payload, actor_id=auth.user.id)
    return DepartmentOut.model_validate(dept)


@departments_router.get("/{department_id}", response_model=DepartmentOut)
async def get_department(
    department_id: UUID,
    _auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DepartmentOut:
    return DepartmentOut.model_validate(await DepartmentService(session).get(department_id))


@departments_router.patch("/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    auth: AuthContext = Depends(require_permission("department.manage")),
    session: AsyncSession = Depends(get_db),
) -> DepartmentOut:
    dept = await DepartmentService(session).update(department_id, payload, actor_id=auth.user.id)
    return DepartmentOut.model_validate(dept)


teams_router = APIRouter(prefix="/teams", tags=["teams"])


@teams_router.get("", response_model=Page[TeamOut])
async def list_teams(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    department_id: UUID | None = None,
    is_active: bool | None = None,
    _auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Page[TeamOut]:
    items, total = await TeamService(session).list(
        limit=limit, offset=offset, department_id=department_id, is_active=is_active, q=q
    )
    return Page(
        items=[to_team_out(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@teams_router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    auth: AuthContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> TeamOut:
    return to_team_out(
        await TeamService(session).create(payload, actor_id=auth.user.id),
        include_members=True,
    )


@teams_router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: UUID,
    _auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TeamOut:
    return to_team_out(await TeamService(session).get(team_id), include_members=True)


@teams_router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    auth: AuthContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> TeamOut:
    return to_team_out(
        await TeamService(session).update(team_id, payload, actor_id=auth.user.id),
        include_members=True,
    )


@teams_router.post("/{team_id}/members", response_model=TeamOut)
async def add_team_member(
    team_id: UUID,
    payload: TeamMemberCreate,
    auth: AuthContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> TeamOut:
    return to_team_out(
        await TeamService(session).add_member(team_id, payload, actor_id=auth.user.id),
        include_members=True,
    )


@teams_router.delete("/{team_id}/members/{user_id}", response_model=TeamOut)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    auth: AuthContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> TeamOut:
    return to_team_out(
        await TeamService(session).remove_member(team_id, user_id, actor_id=auth.user.id),
        include_members=True,
    )
