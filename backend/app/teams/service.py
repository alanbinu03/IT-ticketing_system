from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import ConflictError, NotFoundError
from app.departments.repository import DepartmentRepository
from app.teams.models import Team, TeamMember
from app.teams.repository import TeamRepository
from app.teams.schemas import TeamCreate, TeamMemberCreate, TeamUpdate
from app.users.repository import UserRepository


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TeamRepository(session)
        self.departments = DepartmentRepository(session)
        self.users = UserRepository(session)

    async def get(self, team_id: UUID) -> Team:
        team = await self.repo.get_by_id(team_id)
        if team is None:
            raise NotFoundError("Team not found.")
        return team

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        department_id: UUID | None = None,
        is_active: bool | None = None,
        q: str | None = None,
    ) -> tuple[list[Team], int]:
        return await self.repo.list(
            limit=limit,
            offset=offset,
            department_id=department_id,
            is_active=is_active,
            q=q,
        )

    async def create(self, data: TeamCreate, actor_id: UUID) -> Team:
        if await self.departments.get_by_id(data.department_id) is None:
            raise NotFoundError("Department not found.")
        if await self.repo.get_by_code(data.code):
            raise ConflictError("A team with this code already exists.")
        team = Team(
            name=data.name.strip(),
            code=data.code.strip().upper(),
            description=data.description,
            department_id=data.department_id,
            is_active=data.is_active,
        )
        await self.repo.add(team)
        enqueue_event(
            self.session,
            DomainEvent(
                name="team.created",
                entity_type="team",
                entity_id=team.id,
                actor_id=actor_id,
                payload={"new": {"name": team.name, "code": team.code}},
            ),
        )
        return await self.get(team.id)

    async def update(self, team_id: UUID, data: TeamUpdate, actor_id: UUID) -> Team:
        team = await self.get(team_id)
        previous = {"name": team.name, "code": team.code, "is_active": team.is_active}
        updates = data.model_dump(exclude_unset=True)
        if "department_id" in updates and updates["department_id"] is not None:
            if await self.departments.get_by_id(updates["department_id"]) is None:
                raise NotFoundError("Department not found.")
        if "code" in updates and updates["code"]:
            updates["code"] = updates["code"].strip().upper()
            existing = await self.repo.get_by_code(updates["code"])
            if existing and existing.id != team.id:
                raise ConflictError("A team with this code already exists.")
        if "name" in updates and updates["name"]:
            updates["name"] = updates["name"].strip()
        for field, value in updates.items():
            setattr(team, field, value)
        await self.session.flush()
        enqueue_event(
            self.session,
            DomainEvent(
                name="team.updated",
                entity_type="team",
                entity_id=team.id,
                actor_id=actor_id,
                payload={"previous": previous, "new": updates},
            ),
        )
        return await self.get(team.id)

    async def add_member(self, team_id: UUID, data: TeamMemberCreate, actor_id: UUID) -> Team:
        team = await self.get(team_id)
        if await self.users.get_by_id(data.user_id) is None:
            raise NotFoundError("User not found.")
        existing = await self.repo.get_member(team.id, data.user_id)
        if existing:
            existing.is_lead = data.is_lead
        else:
            await self.repo.add_member(
                TeamMember(team_id=team.id, user_id=data.user_id, is_lead=data.is_lead)
            )
        enqueue_event(
            self.session,
            DomainEvent(
                name="team.member_changed",
                entity_type="team",
                entity_id=team.id,
                actor_id=actor_id,
                payload={"new": {"user_id": str(data.user_id), "is_lead": data.is_lead}},
            ),
        )
        await self.session.flush()
        self.session.expire(team, ["members"])
        return await self.get(team.id)

    async def remove_member(self, team_id: UUID, user_id: UUID, actor_id: UUID) -> Team:
        team = await self.get(team_id)
        member = await self.repo.get_member(team.id, user_id)
        if member is None:
            raise NotFoundError("Team member not found.")
        await self.repo.remove_member(member)
        enqueue_event(
            self.session,
            DomainEvent(
                name="team.member_changed",
                entity_type="team",
                entity_id=team.id,
                actor_id=actor_id,
                payload={"previous": {"user_id": str(user_id)}},
            ),
        )
        await self.session.flush()
        self.session.expire(team, ["members"])
        return await self.get(team.id)
