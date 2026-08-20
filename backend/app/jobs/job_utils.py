"""Small, dependency-free helpers shared by scheduled jobs.

Jobs run in a Lambda-shaped process where the useful unit of work is smaller
than the invocation (an RSS source, a user, or a price batch).  These helpers
keep the aggregate result predictable without leaking arbitrary exception
strings into the job-run audit record.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import TypeVar


# Keep both an individual provider message and the aggregate audit message
# bounded.  JobRun.message is operator-facing data and must never contain a
# traceback-sized or unbounded provider response.
MAX_ERROR_DETAIL_LENGTH = 200
MAX_ERROR_SUMMARY_LENGTH = 512
MAX_ERROR_DETAILS = 8

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]+")
# Authorization headers are slightly different from ordinary key/value
# secrets: a Bearer header contains a scheme followed by the credential.  A
# pattern that stops at the first whitespace therefore leaves the credential
# in the audit message (for example, ``Authorization:<redacted>`` followed
# by ``super-secret-token``).  Match the scheme and credential together, while
# stopping at common structured-message delimiters so useful error context
# after the header is retained.
_AUTHORIZATION_RE = re.compile(
    r"""
    (?P<name>(?<![a-z0-9])[\"']?authorization[\"']?)
    (?P<separator>\s*[:=]+\s*)
    (?P<value>
        \"(?:[^\"\\]|\\.)*\"
        | '(?:[^'\\]|\\.)*'
        | [\"']?(?:(?:bearer|basic|digest)\s+)?[^\s,;}\]]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_SECRET_RE = re.compile(
    r"""
    (?P<name>(?<![a-z0-9])[\"']?(?:api[ _-]?key|access[ _-]?token|secret|password)[\"']?)
    (?P<separator>\s*[:=]+\s*)
    (?P<value>
        \"(?:[^\"\\]|\\.)*\"
        | '(?:[^'\\]|\\.)*'
        | [^\s,;}\]]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

T = TypeVar("T")


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    # The ellipsis is deliberately ASCII so the stored value is safe for all
    # DynamoDB / log consumers and the returned length is deterministic.
    return value[: max(0, limit - 3)] + "..."


def sanitize_error(value: object, *, limit: int = MAX_ERROR_DETAIL_LENGTH) -> str:
    """Return a short, single-line, non-sensitive description of an error."""

    if isinstance(value, BaseException):
        detail = getattr(value, "detail", None) or str(value)
        if not detail:
            detail = type(value).__name__
    else:
        detail = str(value)

    # Replace control characters before collapsing whitespace.  This avoids
    # an exception message forging additional log/audit lines.
    text = _CONTROL_RE.sub(" ", str(detail))

    def redact(match: re.Match[str]) -> str:
        # Keep the field name and its separator so operators can still tell
        # which setting/header caused the failure, but never retain its value.
        return f"{match.group('name')}{match.group('separator')}<redacted>"

    # Authorization must run first because it has a two-part Bearer value;
    # the ordinary key/value pass intentionally handles the other secret
    # shapes independently.
    text = _AUTHORIZATION_RE.sub(redact, text)
    text = _SECRET_RE.sub(redact, text)
    text = " ".join(text.split())
    if not text:
        text = "job unit failed"
    return _truncate(text, max(1, int(limit)))


def error_summary(
    errors: Iterable[str],
    *,
    limit: int = MAX_ERROR_SUMMARY_LENGTH,
    max_details: int = MAX_ERROR_DETAILS,
) -> str | None:
    """Join bounded error details into one bounded aggregate message."""

    values = [sanitize_error(error) for error in errors]
    if not values:
        return None

    cap = max(1, int(max_details))
    visible = values[:cap]
    summary = "; ".join(visible)
    if len(values) > cap:
        summary += f"; +{len(values) - cap} more failures"
    return _truncate(summary, max(1, int(limit)))


def aggregate_status(
    attempted: int,
    failed: int,
    *,
    degraded: bool = False,
) -> str:
    """Classify a job from independent work-unit outcomes.

    ``skipped`` is reserved for a disabled job and is created by callers.  An
    enabled job with no units is a successful no-op.  ``error`` means every
    attempted unit raised; ``partial`` means some work completed but an error
    or degraded result was observed.
    """

    attempted = max(0, int(attempted))
    failed = max(0, min(int(failed), attempted))
    if attempted == 0:
        return "success"
    if failed >= attempted:
        return "error"
    if failed or degraded:
        return "partial"
    return "success"


def chunks(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield non-empty, bounded lists while preserving input order."""

    cap = max(1, int(size))
    current: list[T] = []
    for item in items:
        current.append(item)
        if len(current) >= cap:
            yield current
            current = []
    if current:
        yield current


__all__ = [
    "MAX_ERROR_DETAIL_LENGTH",
    "MAX_ERROR_SUMMARY_LENGTH",
    "MAX_ERROR_DETAILS",
    "aggregate_status",
    "chunks",
    "error_summary",
    "sanitize_error",
]
