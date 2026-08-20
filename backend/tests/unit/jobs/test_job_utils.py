"""Regression tests for bounded, non-sensitive job error messages."""

from __future__ import annotations

import pytest

from app.jobs.job_utils import sanitize_error


@pytest.mark.parametrize(
    "detail",
    [
        "Authorization: Bearer super-secret-token",
        "authorization : bearer super-secret-token, upstream returned 401",
        "AUTHORIZATION=Bearer super-secret-token; retry scheduled",
        "Authorization:\tBearer\tsuper-secret-token.",
        '{"Authorization": "Bearer super-secret-token"}',
        "Authorization: Basic super-secret-token",
    ],
)
def test_sanitize_error_redacts_complete_authorization_value(detail: str) -> None:
    sanitized = sanitize_error(detail)

    assert "super-secret-token" not in sanitized
    assert "<redacted>" in sanitized


@pytest.mark.parametrize(
    ("detail", "credential"),
    [
        ("provider failed: api_key=api-secret-value", "api-secret-value"),
        ("provider failed: access-token: access-secret-value", "access-secret-value"),
        ("provider failed: secret = 'secret-value'", "secret-value"),
        ("provider failed: password=the-password", "the-password"),
    ],
)
def test_sanitize_error_preserves_existing_secret_redactions(
    detail: str, credential: str
) -> None:
    sanitized = sanitize_error(detail)

    assert credential not in sanitized
    assert "<redacted>" in sanitized
    assert "provider failed" in sanitized


def test_sanitize_error_keeps_context_after_redacted_header() -> None:
    sanitized = sanitize_error(
        "request failed; Authorization: Bearer super-secret-token; request_id=42"
    )

    assert "super-secret-token" not in sanitized
    assert "request failed" in sanitized
    assert "request_id=42" in sanitized
    assert "\n" not in sanitized
