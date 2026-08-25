from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.email_validation import clean_account_email, normalize_register_email
from app.auth.models import EmailVerification, RefreshToken
from app.auth.passwords import validate_password
from app.auth.rbac import cache_user_permissions, load_cached_permissions
from app.auth.repository import RefreshTokenRepository
from app.auth.security import (
    create_access_token,
    create_registration_token,
    decode_registration_token,
    generate_otp,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    hash_verification_code,
    needs_rehash,
    verify_password,
)
from app.auth.verification_repository import EmailVerificationRepository
from app.common.events import DomainEvent, enqueue_event
from app.common.exceptions import (
    AppError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from app.common.redis import get_redis
from app.config import get_settings
from app.departments.repository import DepartmentRepository
from app.email.service import EmailService, render_template
from app.roles.constants import ROLE_EMPLOYEE
from app.roles.repository import RoleRepository
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserMe
from app.users.serializers import to_user_me

GENERIC_OTP_MESSAGE = "If the email is eligible, a verification code has been sent."
ADMIN_PORTAL_PERMISSION = "admin.portal.access"


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.verification = EmailVerificationRepository(session)
        self.departments = DepartmentRepository(session)
        self.settings = get_settings()

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str, int, UserMe]:
        try:
            email_norm = clean_account_email(email)
        except AppError:
            raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS") from None
        await self._reject_if_rate_limited(email_norm, ip_address)
        user = await self.users.get_by_email(email_norm)
        if user is None or not verify_password(password, user.password_hash):
            await self._record_failed_login(email_norm, ip_address)
            raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")
        if not user.is_active:
            raise UnauthorizedError("This account has been disabled.", code="ACCOUNT_DISABLED")
        await self._clear_login_rate_limit(email_norm, ip_address)
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        user.last_login_at = datetime.now(UTC)
        access, refresh, expires_in, me = await self._issue_tokens(
            user, ip_address=ip_address, user_agent=user_agent, family_id=uuid4()
        )
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.login",
                entity_type="user",
                entity_id=user.id,
                actor_id=user.id,
                payload={"ip_address": ip_address},
            ),
        )
        return access, refresh, expires_in, me

    async def admin_login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str, int, UserMe]:
        access, refresh, expires_in, me = await self.login(
            email, password, ip_address=ip_address, user_agent=user_agent
        )
        if ADMIN_PORTAL_PERMISSION not in me.permissions:
            raise ForbiddenError(
                "This account does not have access to the administration portal.",
                code="ADMIN_ACCESS_DENIED",
            )
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.admin_login",
                entity_type="user",
                entity_id=me.id,
                actor_id=me.id,
                payload={"ip_address": ip_address},
            ),
        )
        return access, refresh, expires_in, me

    async def refresh(
        self,
        raw_token: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str, int, UserMe]:
        token_hash = hash_refresh_token(raw_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        now = datetime.now(UTC)
        if stored is None:
            raise UnauthorizedError("Invalid refresh token.", code="INVALID_REFRESH_TOKEN")
        if stored.revoked_at is not None:
            await self.refresh_tokens.revoke_family(stored.family_id)
            raise UnauthorizedError("Invalid refresh token.", code="INVALID_REFRESH_TOKEN")
        if stored.expires_at <= now:
            raise UnauthorizedError("Refresh token expired.", code="INVALID_REFRESH_TOKEN")
        user = await self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            await self.refresh_tokens.revoke_family(stored.family_id)
            raise UnauthorizedError("This account has been disabled.", code="ACCOUNT_DISABLED")

        stored.revoked_at = now
        access, refresh, expires_in, me = await self._issue_tokens(
            user,
            ip_address=ip_address,
            user_agent=user_agent,
            family_id=stored.family_id,
            replaces=stored,
        )
        return access, refresh, expires_in, me

    async def request_registration_otp(self, email: str, *, ip_address: str | None) -> str:
        email_norm = normalize_register_email(email)
        existing = await self.users.get_by_email(email_norm)
        if existing is not None and existing.email_is_verified:
            return GENERIC_OTP_MESSAGE
        await self._reject_if_otp_limited(email_norm, ip_address)
        now = datetime.now(UTC)
        current = await self.verification.latest_pending_otp(email_norm)
        if current and current.last_sent_at and (now - current.last_sent_at).total_seconds() < self.settings.otp_resend_seconds:
            raise RateLimitedError("Please wait before requesting another code.")
        otp = generate_otp(self.settings.otp_length)
        record = EmailVerification(
            email=email_norm,
            otp_hash=hash_verification_code(email_norm, otp),
            purpose="REGISTRATION",
            expires_at=now + timedelta(minutes=self.settings.otp_expiry_minutes),
            max_attempts=self.settings.otp_max_attempts,
            last_sent_at=now,
            request_ip=ip_address,
            send_count=1,
        )
        await self.verification.add(record)
        minutes = str(self.settings.otp_expiry_minutes)
        body = (
            "Hello,\n\nYour verification code is:\n\n"
            f"{otp}\n\nThis code expires in {minutes} minutes.\n"
            "If you did not request this registration, you can ignore this email.\n"
        )
        html = render_template("registration_otp.html", otp=otp, minutes=minutes)
        try:
            await EmailService.send(
                email_norm,
                "Verify your IT Support account",
                body,
                html=html,
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                "EMAIL_DELIVERY_FAILED",
                "Could not send the verification email. Try again later.",
                503,
            ) from exc
        enqueue_event(
            self.session,
            DomainEvent(
                name="auth.otp_requested",
                entity_type="email_verification",
                entity_id=record.id,
                payload={"email": email_norm, "purpose": "REGISTRATION"},
            ),
        )
        await self._record_otp_request(email_norm, ip_address)
        return GENERIC_OTP_MESSAGE

    async def verify_registration_otp(self, email: str, otp: str) -> str:
        email_norm = email.lower().strip()
        record = await self.verification.latest_pending_otp(email_norm)
        if record is None:
            raise UnauthorizedError("Invalid or expired verification code.", code="INVALID_VERIFICATION_CODE")
        if record.attempt_count >= record.max_attempts:
            raise UnauthorizedError("Invalid or expired verification code.", code="INVALID_VERIFICATION_CODE")
        expected = hash_verification_code(email_norm, otp.strip())
        now = datetime.now(UTC)
        if record.expires_at <= now or not compare_digest(record.otp_hash, expected):
            record.attempt_count += 1
            await self.session.commit()
            raise UnauthorizedError("Invalid or expired verification code.", code="INVALID_VERIFICATION_CODE")
        record.verified_at = now
        enqueue_event(
            self.session,
            DomainEvent(
                name="auth.email_verified",
                entity_type="email_verification",
                entity_id=record.id,
                payload={"email": email_norm},
            ),
        )
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.email_verified",
                entity_type="email_verification",
                entity_id=record.id,
                payload={"email": email_norm},
            ),
        )
        return create_registration_token(email_norm, record.id)

    async def complete_registration(self, registration_token: str, full_name: str, password: str) -> None:
        try:
            email_norm, verification_id = decode_registration_token(registration_token)
        except ValueError as exc:
            raise UnauthorizedError("Registration session expired. Start again.", code="INVALID_REGISTRATION_TOKEN") from exc
        validate_password(password)
        record = await self.verification.get(verification_id)
        if (
            record is None
            or record.email != email_norm
            or record.purpose != "REGISTRATION"
            or record.verified_at is None
            or record.consumed_at is not None
        ):
            raise UnauthorizedError("Registration session expired. Start again.", code="INVALID_REGISTRATION_TOKEN")
        existing = await self.users.get_by_email(email_norm)
        if existing is not None and existing.email_is_verified:
            record.consumed_at = datetime.now(UTC)
            return
        employee_role = await self.roles.get_by_name(ROLE_EMPLOYEE)
        if employee_role is None:
            raise NotFoundError("Employee role is not configured.")
        department = await self.departments.get_by_code("GEN")
        if department is None:
            department = await self.departments.get_by_code("OPS")
        now = datetime.now(UTC)
        if existing is not None:
            user = existing
            user.full_name = full_name.strip()
            user.password_hash = hash_password(password)
            user.is_active = True
            user.is_verified = True
            user.email_verified_at = now
            if department is not None:
                user.department_id = department.id
            await self.users.set_roles(user, [employee_role])
        else:
            user = User(
                email=email_norm,
                full_name=full_name.strip(),
                password_hash=hash_password(password),
                department_id=department.id if department else None,
                is_active=True,
                is_verified=True,
                email_verified_at=now,
            )
            await self.users.add(user)
            await self.users.set_roles(user, [employee_role])
        record.consumed_at = now
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.registered",
                entity_type="user",
                entity_id=user.id,
                actor_id=user.id,
                payload={"new": {"email": user.email, "full_name": user.full_name, "roles": [ROLE_EMPLOYEE]}},
            ),
        )
        enqueue_event(
            self.session,
            DomainEvent(
                name="user.created",
                entity_type="user",
                entity_id=user.id,
                actor_id=user.id,
                payload={"new": {"email": user.email, "full_name": user.full_name}},
            ),
        )

    async def logout(self, raw_token: str) -> None:
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_token))
        if stored and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)

    async def build_user_me(self, user: User) -> UserMe:
        await self.session.flush()
        loaded = await self.users.get_by_id(user.id)
        if loaded is None:
            raise UnauthorizedError()
        cached = await load_cached_permissions(loaded.id)
        if cached is None:
            cached = await self.roles.get_user_permission_codes(loaded.id)
            await cache_user_permissions(loaded.id, cached)
        role_names = await self.roles.get_user_role_names(loaded.id)
        team_ids = [m.team_id for m in loaded.team_memberships]
        return to_user_me(loaded, roles=role_names, permissions=sorted(cached), team_ids=team_ids)

    async def _issue_tokens(
        self,
        user: User,
        *,
        ip_address: str | None,
        user_agent: str | None,
        family_id: UUID,
        replaces: RefreshToken | None = None,
    ) -> tuple[str, str, int, UserMe]:
        access, expires_in = create_access_token(user.id)
        raw_refresh = generate_refresh_token()
        record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            family_id=family_id,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
            user_agent=(user_agent or "")[:300] or None,
            ip_address=ip_address,
        )
        await self.refresh_tokens.add(record)
        if replaces is not None:
            replaces.replaced_by_id = record.id
        me = await self.build_user_me(user)
        return access, raw_refresh, expires_in, me

    def _rate_limit_key(self, email: str, ip_address: str | None) -> str:
        return f"rl:login:{ip_address or 'unknown'}:{email}"

    def _otp_rate_keys(self, email: str, ip_address: str | None) -> list[str]:
        return [f"rl:otp:email:{email}", f"rl:otp:ip:{ip_address or 'unknown'}"]

    async def _reject_if_otp_limited(self, email: str, ip_address: str | None) -> None:
        if self.settings.app_env.lower() == "test":
            return
        try:
            client = await get_redis()
            for key in self._otp_rate_keys(email, ip_address):
                raw = await client.get(key)
                if raw and int(raw) >= self.settings.otp_max_sends_per_hour:
                    raise RateLimitedError("Too many verification requests. Try again later.")
        except RateLimitedError:
            raise
        except Exception:
            return

    async def _record_otp_request(self, email: str, ip_address: str | None) -> None:
        if self.settings.app_env.lower() == "test":
            return
        try:
            client = await get_redis()
            for key in self._otp_rate_keys(email, ip_address):
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, 3600)
        except Exception:
            return

    async def _reject_if_rate_limited(self, email: str, ip_address: str | None) -> None:
        if self.settings.app_env.lower() == "test":
            return
        try:
            client = await get_redis()
            raw = await client.get(self._rate_limit_key(email, ip_address))
            if raw and int(raw) >= self.settings.login_rate_limit_attempts:
                raise RateLimitedError("Too many login attempts. Try again later.")
        except RateLimitedError:
            raise
        except Exception:
            return

    async def _record_failed_login(self, email: str, ip_address: str | None) -> None:
        if self.settings.app_env.lower() == "test":
            return
        try:
            client = await get_redis()
            key = self._rate_limit_key(email, ip_address)
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, self.settings.login_rate_limit_window_seconds)
        except Exception:
            return

    async def _clear_login_rate_limit(self, email: str, ip_address: str | None) -> None:
        try:
            client = await get_redis()
            await client.delete(self._rate_limit_key(email, ip_address))
        except Exception:
            return
