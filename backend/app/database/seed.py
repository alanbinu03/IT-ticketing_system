"""Idempotent development seed: roles, permissions, org units, and demo users."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import UTC, datetime

from app.auth.security import hash_password
from app.categories.models import Category
from app.config import get_settings
from app.database.session import dispose_engine, get_session_factory, import_models
from app.departments.models import Department
from app.roles.constants import (
    OBSOLETE_ROLES,
    PERMISSIONS,
    ROLE_ADMIN,
    ROLE_EMPLOYEE,
    ROLE_PERMISSION_MAP,
    SYSTEM_ROLES,
)
from app.roles.models import Permission, Role, RolePermission, UserRole
from app.teams.models import Team, TeamMember
from app.tickets.models import Tag
from app.users.models import User

logger = structlog.get_logger(__name__)

DEPARTMENTS = (
    ("Finance", "FIN", "Finance and accounting"),
    ("HR", "HR", "Human resources"),
    ("Operations", "OPS", "Business operations"),
    ("Engineering", "ENG", "Product engineering"),
    ("Administration", "ADM", "Administration"),
    ("Sales", "SAL", "Sales"),
    ("IT", "IT", "Information technology"),
    ("General", "GEN", "Default department for provisioned employees"),
)

IT_TEAMS = (
    ("Service Desk", "SVC", "First-line support"),
    ("Network", "NET", "Network and connectivity"),
    ("Infrastructure", "INFRA", "Servers and platforms"),
    ("Hardware", "HW", "End-user hardware"),
    ("Business Applications", "BA", "Line-of-business applications"),
    ("Security", "SEC", "Information security"),
)

CATEGORIES = (
    ("Hardware", ("Laptop", "Desktop", "Printer", "Peripheral")),
    ("Network", ("Internet", "Wi-Fi", "VPN", "LAN")),
    ("Software", ("ERP", "Email", "Microsoft Office", "Internal Application")),
    ("Access", ("Account Creation", "Password Reset", "Permission Request")),
)

TAGS = (
    ("vpn", "VPN"),
    ("printer", "Printer"),
    ("payroll", "Payroll"),
    ("security", "Security"),
    ("urgent", "Urgent"),
    ("remote-office", "Remote office"),
)


async def _get_or_create_department(
    session: AsyncSession, name: str, code: str, description: str
) -> Department:
    result = await session.execute(select(Department).where(Department.code == code))
    department = result.scalar_one_or_none()
    if department is None:
        department = Department(name=name, code=code, description=description, is_active=True)
        session.add(department)
        await session.flush()
    return department


async def seed(session: AsyncSession) -> None:
    settings = get_settings()
    permission_by_code: dict[str, Permission] = {}
    for code, name, description in PERMISSIONS:
        result = await session.execute(select(Permission).where(Permission.code == code))
        permission = result.scalar_one_or_none()
        if permission is None:
            permission = Permission(code=code, name=name, description=description)
            session.add(permission)
            await session.flush()
        permission_by_code[code] = permission

    role_by_name: dict[str, Role] = {}
    for role_name in SYSTEM_ROLES:
        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(
                name=role_name,
                description=f"System role: {role_name}",
                is_system=True,
            )
            session.add(role)
            await session.flush()
        role_by_name[role_name] = role
        codes = ROLE_PERMISSION_MAP[role_name]
        await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        for code in codes:
            session.add(RolePermission(role_id=role.id, permission_id=permission_by_code[code].id))

    for obsolete_name in OBSOLETE_ROLES:
        result = await session.execute(select(Role).where(Role.name == obsolete_name))
        obsolete = result.scalar_one_or_none()
        if obsolete is not None:
            await session.execute(delete(UserRole).where(UserRole.role_id == obsolete.id))
            await session.execute(delete(RolePermission).where(RolePermission.role_id == obsolete.id))
            await session.delete(obsolete)
            await session.flush()

    departments: dict[str, Department] = {}
    for name, code, description in DEPARTMENTS:
        departments[code] = await _get_or_create_department(session, name, code, description)

    it_dept = departments["IT"]
    teams: dict[str, Team] = {}
    for name, code, description in IT_TEAMS:
        result = await session.execute(select(Team).where(Team.code == code))
        team = result.scalar_one_or_none()
        if team is None:
            team = Team(
                name=name,
                code=code,
                description=description,
                department_id=it_dept.id,
                is_active=True,
            )
            session.add(team)
            await session.flush()
        teams[code] = team

    for parent_name, children in CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == parent_name, Category.parent_id.is_(None))
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            parent = Category(name=parent_name, is_active=True)
            session.add(parent)
            await session.flush()
        for child_name in children:
            existing_child = await session.execute(
                select(Category).where(Category.name == child_name, Category.parent_id == parent.id)
            )
            if existing_child.scalar_one_or_none() is None:
                session.add(Category(name=child_name, parent_id=parent.id, is_active=True))

    for slug, name in TAGS:
        result = await session.execute(select(Tag).where(Tag.slug == slug))
        if result.scalar_one_or_none() is None:
            session.add(Tag(slug=slug, name=name))

    async def upsert_user(
        *,
        email: str,
        password: str,
        full_name: str,
        employee_code: str,
        department: Department,
        role: Role,
        team: Team | None = None,
        is_lead: bool = False,
    ) -> User:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if user is None:
            result = await session.execute(select(User).where(User.employee_code == employee_code))
            user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=email.lower(),
                password_hash=hash_password(password),
                full_name=full_name,
                employee_code=employee_code,
                department_id=department.id,
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.now(UTC),
            )
            session.add(user)
            await session.flush()
        else:
            user.email = email.lower()
            user.password_hash = hash_password(password)
            user.full_name = full_name
            user.employee_code = employee_code
            user.department_id = department.id
            user.is_active = True
            user.is_verified = True
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
        await session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        session.add(UserRole(user_id=user.id, role_id=role.id))
        if team is not None:
            existing = await session.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team.id, TeamMember.user_id == user.id
                )
            )
            if existing.scalar_one_or_none() is None:
                session.add(TeamMember(team_id=team.id, user_id=user.id, is_lead=is_lead))
        return user

    admin_role = role_by_name[ROLE_ADMIN]
    if settings.initial_admin_email and settings.initial_admin_password:
        await upsert_user(
            email=settings.initial_admin_email,
            password=settings.initial_admin_password,
            full_name=settings.initial_admin_name or "System Administrator",
            employee_code="EMP-SYSADMIN",
            department=it_dept,
            role=admin_role,
            team=teams["SVC"],
        )
    admin_members = (
        (settings.seed_admin_email, "Hardik", "EMP-HARDIK"),
        (settings.seed_admin_ronald_email, "Ronald", "EMP-RONALD"),
        (settings.seed_admin_sanjay_email, "Sanjay", "EMP-SANJAY"),
    )
    keep_emails = {settings.seed_employee_email.lower()}
    if settings.initial_admin_email:
        keep_emails.add(settings.initial_admin_email.lower())
    for email, full_name, employee_code in admin_members:
        keep_emails.add(email.lower())
        await upsert_user(
            email=email,
            password=settings.seed_admin_password,
            full_name=full_name,
            employee_code=employee_code,
            department=it_dept,
            role=admin_role,
            team=teams["SVC"],
        )

    await upsert_user(
        email=settings.seed_employee_email,
        password=settings.seed_employee_password,
        full_name="Jordan Lee",
        employee_code="EMP-USER",
        department=departments["ENG"],
        role=role_by_name[ROLE_EMPLOYEE],
    )

    leftover_emails = ("admin@example.com", "agent@example.com")
    leftover_codes = ("EMP-ADMIN", "EMP-AGENT")
    for email in leftover_emails:
        if email.lower() in keep_emails:
            continue
        result = await session.execute(select(User).where(User.email == email))
        leftover = result.scalar_one_or_none()
        if leftover is not None:
            leftover.is_active = False
    for code in leftover_codes:
        result = await session.execute(select(User).where(User.employee_code == code))
        leftover = result.scalar_one_or_none()
        if leftover is not None and leftover.email.lower() not in keep_emails:
            leftover.is_active = False

    test_leftovers = await session.execute(
        select(User).where(
            (User.full_name == "Riley Chen")
            | User.email.like("adminish-%@example.com")
            | User.email.like("agentish-%@example.com")
        )
    )
    for leftover in test_leftovers.scalars():
        leftover.is_active = False
        await session.execute(delete(UserRole).where(UserRole.user_id == leftover.id))

    await session.commit()
    from app.auth.rbac import invalidate_role_permission_cache

    await invalidate_role_permission_cache()
    logger.info("seed_completed")


async def _run() -> None:
    import_models()
    factory = get_session_factory()
    async with factory() as session:
        await seed(session)
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_run())
