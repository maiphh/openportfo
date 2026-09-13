"""SMTP EmailSender adapter (smtplib confined here). Gmail App Password demo path."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage as SmtpMessage
from typing import Any, Callable, Optional

from app.ports.email import EmailMessage, EmailSendError

SmtpFactory = Callable[[str, int], Any]


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str = "",
        smtp_factory: Optional[SmtpFactory] = None,
    ) -> None:
        self._host = (host or "").strip() or "smtp.gmail.com"
        self._port = int(port or 587)
        self._username = (username or "").strip()
        self._password = (password or "").replace(" ", "")
        self._from = (from_address or "").strip() or self._username
        self._smtp_factory = smtp_factory

    def send(self, message: EmailMessage) -> None:
        if not self._username or not self._password:
            raise EmailSendError("SMTP_USERNAME / SMTP_PASSWORD are not configured")
        to = (message.to or "").strip()
        if not to:
            raise EmailSendError("recipient is empty")
        if not self._from:
            raise EmailSendError("SMTP from-address is empty")
        payload = SmtpMessage()
        payload["From"] = self._from
        payload["To"] = to
        payload["Subject"] = message.subject or ""
        payload.set_content(message.text_body or "")
        html = (message.html_body or "").strip()
        if html:
            payload.add_alternative(html, subtype="html")
        factory = self._smtp_factory or _default_smtp
        client = factory(self._host, self._port)
        try:
            client.starttls()
            client.login(self._username, self._password)
            client.send_message(payload)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailSendError(str(exc) or "SMTP send failed") from exc
        finally:
            close = getattr(client, "quit", None) or getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 - best-effort close
                    pass


def _default_smtp(host: str, port: int) -> smtplib.SMTP:
    return smtplib.SMTP(host, port, timeout=20)


__all__ = ["SmtpEmailSender"]
