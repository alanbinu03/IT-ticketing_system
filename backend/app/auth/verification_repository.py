from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerification


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, record: EmailVerification) -> EmailVerification:
        self.session.add(record)
        await self.session.flush()
        return record

    async def get(self, verification_id) -> EmailVerification | None:
        return await self.session.get(EmailVerification, verification_id)

    async def latest_open(self, email: str, purpose: str = "REGISTRATION") -> EmailVerification | None:
        result = await self.session.execute(
            select(EmailVerification)
            .where(
                EmailVerification.email == email.lower().strip(),
                EmailVerification.purpose == purpose,
                EmailVerification.consumed_at.is_(None),
            )
            .order_by(EmailVerification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def latest_pending_otp(self, email: str, purpose: str = "REGISTRATION") -> EmailVerification | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(EmailVerification)
            .where(
                EmailVerification.email == email.lower().strip(),
                EmailVerification.purpose == purpose,
                EmailVerification.consumed_at.is_(None),
                EmailVerification.verified_at.is_(None),
                EmailVerification.expires_at > now,
            )
            .order_by(EmailVerification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
