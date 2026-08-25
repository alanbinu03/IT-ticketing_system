from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
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
        if not settings.email_sending_enabled:
            logger.info("email_skipped", to=to_email, subject=subject, reason="email_disabled")
            return
        await EmailService._send_via_nodemailer(
            to_email=to_email,
            subject=subject,
            body=body,
            html=html,
            settings=settings,
        )
        logger.info("email_sent", to=to_email, subject=subject)

    @staticmethod
    async def _send_via_nodemailer(
        *,
        to_email: str,
        subject: str,
        body: str,
        html: str | None,
        settings,
    ) -> None:
        await asyncio.to_thread(
            EmailService._post_mailer,
            settings,
            {
                "to": to_email,
                "subject": subject,
                "text": body,
                "html": html,
            },
        )

    @staticmethod
    def _post_mailer(settings, payload: dict) -> None:
        url = f"{settings.mailer_url.rstrip('/')}/send"
        headers = {"Content-Type": "application/json"}
        if settings.mailer_token:
            headers["Authorization"] = f"Bearer {settings.mailer_token}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status >= 400:
                    raise RuntimeError(f"mailer returned HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"mailer returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"mailer unreachable at {url}: {exc.reason}") from exc
