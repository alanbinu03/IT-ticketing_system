from app.email.service import EmailService, SentEmail, clear_outbox, get_outbox

__all__ = ["EmailService", "SentEmail", "clear_outbox", "get_outbox", "send_email"]


async def send_email(to_email: str, subject: str, body: str) -> None:
    await EmailService.send(to_email, subject, body)
