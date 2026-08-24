from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.teams.models import Team, TeamMember


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, team_id: UUID) -> Team | None:
        result = await self.session.execute(
            select(Team)
            .options(
                selectinload(Team.department),
                selectinload(Team.members).selectinload(TeamMember.user),
            )
            .where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Team | None:
        result = await self.session.execute(
            select(Team).where(func.lower(Team.code) == code.lower())
        )
        return result.scalar_one_or_none()

    def _filters(
        self,
        stmt,
        *,
        department_id: UUID | None,
        is_active: bool | None,
        q: str | None,
    ):
        if department_id is not None:
            stmt = stmt.where(Team.department_id == department_id)
        if is_active is not None:
            stmt = stmt.where(Team.is_active.is_(is_active))
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(Team.name.ilike(pattern) | Team.code.ilike(pattern))
        return stmt

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        department_id: UUID | None = None,
        is_active: bool | None = None,
        q: str | None = None,
    ) -> tuple[list[Team], int]:
        total = int(
            (
                await self.session.execute(
                    self._filters(
                        select(func.count()).select_from(Team),
                        department_id=department_id,
                        is_active=is_active,
                        q=q,
                    )
                )
            ).scalar_one()
        )
        rows = await self.session.execute(
            self._filters(
                select(Team).options(selectinload(Team.department)),
                department_id=department_id,
                is_active=is_active,
                q=q,
            )
            .order_by(Team.name)
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().unique().all()), total

    async def add(self, team: Team) -> Team:
        self.session.add(team)
        await self.session.flush()
        return team

    async def get_member(self, team_id: UUID, user_id: UUID) -> TeamMember | None:
        result = await self.session.execute(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_member(self, member: TeamMember) -> TeamMember:
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(self, member: TeamMember) -> None:
        await self.session.delete(member)
        await self.session.flush()
