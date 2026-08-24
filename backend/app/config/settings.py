"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_CANDIDATES = (
    Path(__file__).resolve().parents[3] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
    Path(".env"),
)


def _env_fingerprint() -> tuple[tuple[str, float], ...]:
    stamps: list[tuple[str, float]] = []
    seen: set[str] = set()
    for path in _ENV_CANDIDATES:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen or not resolved.is_file():
            continue
        seen.add(key)
        stamps.append((key, resolved.stat().st_mtime))
    return tuple(stamps)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "IT Ticketing System"
    app_debug: bool = False
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+asyncpg://ticketing:ticketing@localhost:5433/ticketing"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_pool_recycle_seconds: int = 1800

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ticketing-attachments"
    minio_use_ssl: bool = False

    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 60
    otp_expiry_minutes: int = 10
    otp_length: int = 6
    otp_max_attempts: int = 5
    otp_resend_seconds: int = 60
    otp_max_sends_per_hour: int = 5
    registration_token_expire_minutes: int = 15

    max_request_bytes: int = 10 * 1024 * 1024
    rbac_cache_ttl_seconds: int = 60

    initial_admin_email: str = ""
    initial_admin_password: str = ""
    initial_admin_name: str = ""
    default_it_notification_emails: str = ""
    seed_admin_email: str = "hardik@example.com"
    seed_admin_password: str = "ChangeMe!Admin123"
    seed_admin_ronald_email: str = "ronald@example.com"
    seed_admin_sanjay_email: str = "sanjay@example.com"
    seed_employee_email: str = "employee@example.com"
    seed_employee_password: str = "ChangeMe!Employee123"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@localhost"
    smtp_from_name: str = "IT Support"
    smtp_use_tls: bool = True
    allowed_email_domains: str = ""
    email_check_deliverability: bool = True
    verification_code_ttl_minutes: int = 10
    frontend_url: str = "http://localhost:5173"

    @field_validator("jwt_secret")
    @classmethod
    def secret_not_placeholder_in_production(cls, value: str, info):
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}

    @property
    def allowed_email_domain_list(self) -> list[str]:
        return [item.strip().lower() for item in self.allowed_email_domains.split(",") if item.strip()]

    @property
    def it_notification_email_list(self) -> list[str]:
        return [
            item.strip().lower()
            for item in self.default_it_notification_emails.split(",")
            if item.strip()
        ]


_settings_cache: Settings | None = None
_settings_fingerprint: tuple[tuple[str, float], ...] | None = None


def get_settings() -> Settings:
    """Reload settings when a .env file changes so ALLOWED_EMAIL_DOMAINS takes effect without a full restart."""
    global _settings_cache, _settings_fingerprint
    fingerprint = _env_fingerprint()
    if _settings_cache is None or _settings_fingerprint != fingerprint:
        _settings_cache = Settings()
        _settings_fingerprint = fingerprint
    return _settings_cache


def _clear_settings_cache() -> None:
    global _settings_cache, _settings_fingerprint
    _settings_cache = None
    _settings_fingerprint = None


get_settings.cache_clear = _clear_settings_cache  # type: ignore[attr-defined]
