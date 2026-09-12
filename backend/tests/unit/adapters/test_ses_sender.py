"""SES adapter unit tests (stubbed boto3 client)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.adapters.ses.sender import SesEmailSender
from app.ports.email import EmailMessage, EmailSendError


def test_ses_sender_calls_send_email() -> None:
    client = MagicMock()
    sender = SesEmailSender(from_address="from@example.com", client=client)
    sender.send(
        EmailMessage(
            to="user@example.com",
            subject="Hello",
            text_body="plain",
            html_body="<p>html</p>",
        )
    )
    client.send_email.assert_called_once()
    kwargs = client.send_email.call_args.kwargs
    assert kwargs["Source"] == "from@example.com"
    assert kwargs["Destination"]["ToAddresses"] == ["user@example.com"]
    assert kwargs["Message"]["Subject"]["Data"] == "Hello"
    assert kwargs["Message"]["Body"]["Text"]["Data"] == "plain"
    assert kwargs["Message"]["Body"]["Html"]["Data"] == "<p>html</p>"


def test_ses_sender_requires_from_address() -> None:
    sender = SesEmailSender(from_address="", client=MagicMock())
    with pytest.raises(EmailSendError, match="SES_FROM_EMAIL"):
        sender.send(EmailMessage(to="a@b.com", subject="x", text_body="y"))


def test_ses_sender_wraps_client_error() -> None:
    client = MagicMock()
    client.send_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "sandbox"}},
        "SendEmail",
    )
    sender = SesEmailSender(from_address="from@example.com", client=client)
    with pytest.raises(EmailSendError):
        sender.send(EmailMessage(to="a@b.com", subject="x", text_body="y"))
