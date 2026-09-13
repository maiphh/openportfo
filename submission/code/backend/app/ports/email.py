"""Outbound email port (SES in prod; recording fake in tests)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: Optional[str] = None


class EmailSendError(Exception):
    """Raised when the adapter cannot deliver one message."""

    def __init__(self, detail: str = "Email send failed") -> None:
        self.detail = detail
        super().__init__(detail)


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Deliver one message. Raises EmailSendError on failure."""
        ...


__all__ = ["EmailMessage", "EmailSendError", "EmailSender"]
