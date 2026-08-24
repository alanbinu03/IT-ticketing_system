from __future__ import annotations

import asyncio
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_outbox: list["SentEmail"] = []


@dataclass(slots=True)
class SentEmail:
    to_email: str
    subject: str
    body: str


def get_outbox() -> list[SentEmail]:
    return _outbox


def clear_outbox() -> None:
    _outbox.clear()


def render_template(name: str, **values: str) -> str:
    content = (_TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    base = (_TEMPLATE_DIR / "base.html").read_text(encoding="utf-8")
    return base.replace("{{content}}", content)


class EmailService:
    @staticmethod
    async def send(to_email: str, subject: str, body: str, *, html: str | None = None) -> None:
        settings = get_settings()
        _outbox.append(SentEmail(to_email=to_email, subject=subject, body=body))
        if not settings.smtp_host:
            logger.info("email_console", to=to_email, subject=subject, body=body)
            return
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = to_email
        message.set_content(body)
        if html:
            message.add_alternative(html, subtype="html")
        await asyncio.to_thread(EmailService._send_smtp, message, settings)
        logger.info("email_sent", to=to_email, subject=subject)

    @staticmethod
    def _send_smtp(message: EmailMessage, settings) -> None:
        import smtplib

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
            if settings.smtp_use_tls:
                client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
