from __future__ import annotations

from uuid import UUID

from app.teams.models import Team
from app.teams.schemas import DepartmentRef as TeamDepartmentRef, TeamMemberOut, TeamOut
from app.users.models import User
from app.users.schemas import DepartmentRef, UserMe, UserOut


def to_user_out(user: User) -> UserOut:
    roles = [ur.role.name for ur in user.user_roles]
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        employee_code=user.employee_code,
        username=user.username,
        department_id=user.department_id,
        department=DepartmentRef.model_validate(user.department) if user.department else None,
        manager_id=user.manager_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
    )


def to_user_me(
    user: User,
    *,
    roles: list[str],
    permissions: list[str],
    team_ids: list[UUID],
) -> UserMe:
    base = to_user_out(user)
    return UserMe(**base.model_dump(), permissions=permissions, team_ids=team_ids)


def to_team_out(team: Team, *, include_members: bool = False) -> TeamOut:
    members = None
    if include_members:
        members = [
            TeamMemberOut(
                user_id=member.user_id,
                full_name=member.user.full_name if member.user else "",
                email=member.user.email if member.user else "",
                is_lead=member.is_lead,
            )
            for member in team.members
        ]
    return TeamOut(
        id=team.id,
        name=team.name,
        code=team.code,
        description=team.description,
        department_id=team.department_id,
        department=TeamDepartmentRef.model_validate(team.department) if team.department else None,
        is_active=team.is_active,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=members,
    )
