"""In-memory EmailSender for local/dev and unit tests."""

from __future__ import annotations

from app.ports.email import EmailMessage, EmailSendError


class InMemoryEmailSender:
    """Records sends; optionally fails for listed recipient addresses."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.fail_for: set[str] = set()

    def send(self, message: EmailMessage) -> None:
        to = (message.to or "").strip().casefold()
        if to in self.fail_for:
            raise EmailSendError(f"forced failure for {message.to}")
        self.sent.append(message)

    def clear(self) -> None:
        self.sent.clear()
        self.fail_for.clear()


__all__ = ["InMemoryEmailSender"]
