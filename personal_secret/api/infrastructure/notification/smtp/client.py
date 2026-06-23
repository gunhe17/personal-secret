from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from personal_secret.api.config import get_email_config
from personal_secret.api.infrastructure.notification.common.client import Notifier
from personal_secret.api.infrastructure.notification.common.exception import NotificationError


# #
# smtp

class Smtp(Notifier):
    async def send(self, *, to: str, subject: str, body: str) -> None:
        await asyncio.to_thread(self._send, to, subject, body)

    def _send(self, to: str, subject: str, body: str) -> None:
        config = get_email_config()

        message = EmailMessage()
        message["From"] = config.SMTP_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.send_message(message)

        except (smtplib.SMTPException, OSError) as exc:
            raise NotificationError(reason=str(exc))


# #
# client

smtp = Smtp()
