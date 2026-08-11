"""Optional live AWS smoke tests — skipped unless RUN_AWS_TESTS=1.

Does not run in default unit suite.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.aws


def _aws_enabled() -> bool:
    return os.environ.get("RUN_AWS_TESTS", "").strip() in ("1", "true", "True", "yes")


@pytest.mark.skipif(not _aws_enabled(), reason="Set RUN_AWS_TESTS=1 for live AWS smoke")
def test_sts_caller_identity() -> None:
    import boto3

    ident = boto3.client("sts").get_caller_identity()
    assert "Account" in ident
    assert "Arn" in ident


@pytest.mark.skipif(not _aws_enabled(), reason="Set RUN_AWS_TESTS=1 for live AWS smoke")
def test_eb_health_if_url_set() -> None:
    url = (os.environ.get("EB_HEALTH_URL") or "").strip()
    if not url:
        pytest.skip("EB_HEALTH_URL not set")
    import httpx

    resp = httpx.get(url, timeout=15.0)
    assert resp.status_code == 200
