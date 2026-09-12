"""SMTP EmailSender unit tests (mocked smtplib client)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.adapters.smtp.sender import SmtpEmailSender
from app.core.config import Settings
from app.core.deps import build_email_sender
from app.ports.email import EmailMessage, EmailSendError


def test_smtp_sender_starttls_login_and_send() -> None:
    client = MagicMock()
    factory = MagicMock(return_value=client)
    sender = SmtpEmailSender(
        host="smtp.gmail.com",
        port=587,
        username="maiphh29@gmail.com",
        password="abcd efgh ijkl mnop",
        from_address="",
        smtp_factory=factory,
    )
    sender.send(
        EmailMessage(
            to="maiphh29@gmail.com",
            subject="OpenPortfo daily update",
            text_body="plain",
            html_body="<p>html</p>",
        )
    )
    factory.assert_called_once_with("smtp.gmail.com", 587)
    client.starttls.assert_called_once()
    client.login.assert_called_once_with("maiphh29@gmail.com", "abcdefghijklmnop")
    sent = client.send_message.call_args.args[0]
    assert sent["From"] == "maiphh29@gmail.com"
    assert sent["To"] == "maiphh29@gmail.com"
    assert sent["Subject"] == "OpenPortfo daily update"
    client.quit.assert_called_once()


def test_smtp_sender_requires_credentials() -> None:
    sender = SmtpEmailSender(
        host="smtp.gmail.com",
        port=587,
        username="",
        password="",
        from_address="a@b.com",
        smtp_factory=MagicMock(),
    )
    with pytest.raises(EmailSendError, match="SMTP"):
        sender.send(EmailMessage(to="a@b.com", subject="x", text_body="y"))


def test_smtp_sender_wraps_smtp_error() -> None:
    client = MagicMock()
    client.login.side_effect = OSError("auth")
    sender = SmtpEmailSender(
        host="smtp.gmail.com",
        port=587,
        username="a@b.com",
        password="pw",
        from_address="a@b.com",
        smtp_factory=lambda _h, _p: client,
    )
    with pytest.raises(EmailSendError):
        sender.send(EmailMessage(to="a@b.com", subject="x", text_body="y"))


def test_build_email_sender_prefers_smtp_over_ses() -> None:
    settings = Settings(
        APP_ENV="local",
        STORAGE_BACKEND="aws",
        SMTP_USERNAME="a@gmail.com",
        SMTP_PASSWORD="app-pass",
        SES_FROM_EMAIL="unused@example.com",
    )
    sender = build_email_sender(settings)
    assert sender.__class__.__name__ == "SmtpEmailSender"


def test_build_email_sender_memory_without_smtp_or_aws() -> None:
    settings = Settings(APP_ENV="local", STORAGE_BACKEND="memory", USE_AWS_ADAPTERS=False)
    sender = build_email_sender(settings)
    assert sender.__class__.__name__ == "InMemoryEmailSender"
