from __future__ import annotations

from email_validator import EmailNotValidError, validate_email

from app.common.exceptions import AppError
from app.config import get_settings

PUBLIC_EMAIL_PROVIDERS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.in",
        "yahoo.co.uk",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "icloud.com",
        "me.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "gmx.com",
        "mail.com",
        "yandex.com",
        "zoho.com",
    }
)


def normalize_email(raw: str) -> str:
    try:
        result = validate_email(raw.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise AppError("INVALID_EMAIL", "Enter a valid email address.", 400) from exc
    return result.normalized.lower()


def parsed_email_domain(email: str) -> str:
    if "@" not in email:
        raise AppError("INVALID_EMAIL", "Enter a valid email address.", 400)
    return email.rsplit("@", 1)[1].lower()


def is_allowed_company_email(email: str) -> bool:
    normalized = normalize_email(email)
    domain = parsed_email_domain(normalized)
    if domain in PUBLIC_EMAIL_PROVIDERS:
        return False
    allowed = get_settings().allowed_email_domain_list
    if not allowed:
        return False
    return domain in allowed


def normalize_register_email(raw: str) -> str:
    settings = get_settings()
    check_mx = settings.email_check_deliverability and settings.app_env.lower() != "test"
    try:
        result = validate_email(raw.strip(), check_deliverability=check_mx)
    except EmailNotValidError as exc:
        raise AppError("INVALID_EMAIL", "Enter a valid email address.", 400) from exc
    email = result.normalized.lower()
    if not is_allowed_company_email(email):
        raise AppError("EMAIL_DOMAIN_NOT_ALLOWED", company_email_rejection_message(), 400)
    return email


def company_email_rejection_message() -> str:
    domains = get_settings().allowed_email_domain_list
    if not domains:
        return "Self-registration is not enabled."
    listed = " or ".join(f"@{domain}" for domain in domains)
    return f"Use a company email ending in {listed}."
