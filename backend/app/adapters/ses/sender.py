"""Amazon SES EmailSender adapter (boto3 confined here)."""

from __future__ import annotations

from typing import Any, Optional

from botocore.exceptions import BotoCoreError, ClientError

from app.ports.email import EmailMessage, EmailSendError


class SesEmailSender:
    def __init__(
        self,
        *,
        from_address: str,
        region: str = "us-east-1",
        client: Any = None,
    ) -> None:
        self._from = (from_address or "").strip()
        self._region = region or "us-east-1"
        self._client = client

    def _ses(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("ses", region_name=self._region)
        return self._client

    def send(self, message: EmailMessage) -> None:
        if not self._from:
            raise EmailSendError("SES_FROM_EMAIL is not configured")
        to = (message.to or "").strip()
        if not to:
            raise EmailSendError("recipient is empty")
        body: dict[str, Any] = {"Text": {"Data": message.text_body or "", "Charset": "UTF-8"}}
        html = (message.html_body or "").strip()
        if html:
            body["Html"] = {"Data": html, "Charset": "UTF-8"}
        try:
            self._ses().send_email(
                Source=self._from,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": message.subject or "", "Charset": "UTF-8"},
                    "Body": body,
                },
            )
        except (ClientError, BotoCoreError) as exc:
            raise EmailSendError(getattr(exc, "response", None) and str(exc) or str(exc)) from exc
