"""Daily SES portfolio email job (opt-in users; snapshot + related news)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import uuid4

from app.jobs.context import JobContext
from app.jobs.job_utils import (
    MAX_ERROR_DETAILS,
    MAX_ERROR_SUMMARY_LENGTH,
    aggregate_status,
    error_summary,
    ict_today,
    sanitize_error,
)
from app.ports.admin import JobRun
from app.ports.email import EmailMessage, EmailSendError
from app.ports.news import NewsItem
from app.ports.snapshots import SnapshotRecord
from app.ports.users import UserProfile

MAX_HOLDING_ROWS = 30
MAX_NEWS_ITEMS = 5
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_email(value: Optional[str]) -> bool:
    text = (value or "").strip()
    return bool(text) and _EMAIL_RE.match(text) is not None


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _money(value: Optional[Decimal]) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f}"


def _pct(part: Optional[Decimal], whole: Optional[Decimal]) -> str:
    if part is None or whole is None or whole == 0:
        return "n/a"
    return f"{(part / whole) * Decimal('100'):+.2f}%"


def _line_key(line: dict[str, Any]) -> tuple[str, str]:
    return (
        str(line.get("assetType") or "").strip().lower(),
        str(line.get("symbol") or "").strip().upper(),
    )


def _totals_for(payload: dict[str, Any], currency: str) -> dict[str, Any]:
    totals = payload.get("totalsByCurrency") or {}
    if not isinstance(totals, dict):
        return {}
    if currency in totals and isinstance(totals[currency], dict):
        return totals[currency]
    for value in totals.values():
        if isinstance(value, dict):
            return value
    return {}


def _display_currency(profile: UserProfile, payload: dict[str, Any], fallback: str) -> str:
    preferred = (profile.preferred_currency or fallback or "USD").strip().upper()
    totals = payload.get("totalsByCurrency") or {}
    if isinstance(totals, dict) and preferred in totals:
        return preferred
    if isinstance(totals, dict) and totals:
        return str(next(iter(totals.keys())))
    return preferred or "USD"


def _user_needles(ctx: JobContext, user_id: str) -> list[str]:
    seen: set[str] = set()
    needles: list[str] = []
    for holding in ctx.holdings_repo.list(user_id):
        text = str(holding.symbol or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            needles.append(text)
    for item in ctx.watchlist_repo.list(user_id):
        text = str(item.symbol or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            needles.append(text)
    return needles


def _news_matches(item: NewsItem, needles: list[str]) -> bool:
    if not needles:
        return False
    title = (item.title or "").casefold()
    symbols = {str(s).casefold() for s in (item.symbols or []) if s}
    return any(n.casefold() and (n.casefold() in title or n.casefold() in symbols) for n in needles)


def _matched_symbols(item: NewsItem, needles: list[str]) -> list[str]:
    title = (item.title or "").casefold()
    item_syms = {str(s).casefold() for s in (item.symbols or []) if s}
    found: list[str] = []
    seen: set[str] = set()
    for needle in needles:
        key = needle.casefold()
        if not key or key in seen:
            continue
        if key in title or key in item_syms:
            seen.add(key)
            found.append(needle)
    return found


def related_news(ctx: JobContext, user_id: str, *, limit: int = MAX_NEWS_ITEMS) -> tuple[list[NewsItem], list[str]]:
    needles = _user_needles(ctx, user_id)
    if not needles:
        return [], needles
    pool = ctx.news_repo.list_recent(limit=max(limit * 8, 40))
    out: list[NewsItem] = []
    for item in pool:
        if _news_matches(item, needles):
            out.append(item)
        if len(out) >= limit:
            break
    return out, needles


def _iter_profiles(ctx: JobContext):
    iterator = getattr(ctx.user_profile_repo, "iter_all", None)
    if callable(iterator):
        yield from iterator()
        return
    yield from ctx.user_profile_repo.list_all()


def _holding_rows(
    today: SnapshotRecord,
    yesterday: Optional[SnapshotRecord],
) -> list[dict[str, Any]]:
    today_lines = list((today.payload or {}).get("lines") or [])
    yesterday_map: dict[tuple[str, str], dict[str, Any]] = {}
    if yesterday is not None:
        for line in (yesterday.payload or {}).get("lines") or []:
            if isinstance(line, dict):
                yesterday_map[_line_key(line)] = line
    rows: list[dict[str, Any]] = []
    for line in today_lines:
        if not isinstance(line, dict):
            continue
        missing = bool(line.get("missingPrice"))
        value = None if missing else _to_decimal(line.get("marketValue"))
        cost = None if missing else _to_decimal(line.get("costBasis"))
        pnl = None if missing else _to_decimal(line.get("pnl"))
        prev = yesterday_map.get(_line_key(line))
        prev_value = (
            _to_decimal(prev.get("marketValue")) if prev and not prev.get("missingPrice") else None
        )
        day = (value - prev_value) if value is not None and prev_value is not None else None
        rows.append(
            {
                "symbol": str(line.get("symbol") or ""),
                "assetType": str(line.get("assetType") or ""),
                "value": value,
                "pnl": pnl,
                "pnlPct": _pct(pnl, cost),
                "day": day,
                "dayPct": _pct(day, prev_value),
            }
        )
    return rows


def render_email(
    *,
    profile: UserProfile,
    today: SnapshotRecord,
    yesterday: Optional[SnapshotRecord],
    news: list[NewsItem],
    needles: list[str],
    fallback_currency: str,
) -> EmailMessage:
    payload = today.payload or {}
    ccy = _display_currency(profile, payload, fallback_currency)
    today_tot = _totals_for(payload, ccy)
    y_tot = _totals_for(yesterday.payload or {}, ccy) if yesterday is not None else {}
    today_value = _to_decimal(today_tot.get("marketValue"))
    y_value = _to_decimal(y_tot.get("marketValue")) if y_tot else None
    pnl = _to_decimal(today_tot.get("pnl"))
    cost = _to_decimal(today_tot.get("costBasis"))
    day = (today_value - y_value) if today_value is not None and y_value is not None else None
    snapshot_date = today.date
    rows = _holding_rows(today, yesterday)
    extra = max(0, len(rows) - MAX_HOLDING_ROWS)
    visible = rows[:MAX_HOLDING_ROWS]

    lines = [
        f"Portfolio ({ccy}) on {snapshot_date}",
        "",
        f"Value: {_money(today_value)}",
        f"Yesterday: {_money(y_value)}",
        f"Day change: {_money(day)} ({_pct(day, y_value)})",
        f"PnL vs cost: {_money(pnl)} ({_pct(pnl, cost)})",
        "",
        "Holdings",
    ]
    if not visible:
        lines.append("No holdings in today's snapshot.")
    else:
        lines.append("SYMBOL  TYPE    VALUE         PnL vs cost           Day change")
        for row in visible:
            lines.append(
                f"{row['symbol']:<6}  {row['assetType']:<6}  "
                f"{_money(row['value']):<12}  "
                f"{_money(row['pnl'])} ({row['pnlPct']})  "
                f"{_money(row['day'])} ({row['dayPct']})"
            )
        if extra:
            lines.append(f"and {extra} more")
    lines.extend(["", "Related news"])
    if not news:
        lines.append("No related news today.")
    else:
        for item in news:
            matched = ", ".join(_matched_symbols(item, needles))
            extra_match = f" — matched: {matched}" if matched else ""
            lines.append(f"- {item.title} ({item.source or ''}) {item.url or ''}{extra_match}")
    lines.extend(
        [
            "",
            "Turn this off any time in Settings → Receive daily portfolio email.",
        ]
    )
    text = "\n".join(lines)

    html_rows = "".join(
        (
            "<tr>"
            f"<td>{row['symbol']}</td><td>{row['assetType']}</td>"
            f"<td>{_money(row['value'])}</td>"
            f"<td>{_money(row['pnl'])} ({row['pnlPct']})</td>"
            f"<td>{_money(row['day'])} ({row['dayPct']})</td>"
            "</tr>"
        )
        for row in visible
    )
    if extra:
        html_rows += "<tr><td colspan='5'>and " + str(extra) + " more</td></tr>"
    if not visible:
        html_rows = "<tr><td colspan='5'>No holdings in today's snapshot.</td></tr>"
    if not news:
        news_html = "<p>No related news today.</p>"
    else:
        items_html = "".join(
            f'<li><a href="{item.url or "#"}">{item.title}</a> ({item.source or ""})</li>'
            for item in news
        )
        news_html = f"<ul>{items_html}</ul>"
    html = (
        f"<p>Portfolio ({ccy}) on {snapshot_date}</p>"
        f"<p>Value: {_money(today_value)}<br/>"
        f"Yesterday: {_money(y_value)}<br/>"
        f"Day change: {_money(day)} ({_pct(day, y_value)})<br/>"
        f"PnL vs cost: {_money(pnl)} ({_pct(pnl, cost)})</p>"
        "<h3>Holdings</h3>"
        "<table><thead><tr><th>Symbol</th><th>Type</th><th>Value</th>"
        "<th>PnL vs cost</th><th>Day change</th></tr></thead>"
        f"<tbody>{html_rows}</tbody></table>"
        f"<h3>Related news</h3>{news_html}"
        "<p>Turn this off any time in Settings → Receive daily portfolio email.</p>"
    )
    return EmailMessage(
        to=str(profile.email or "").strip(),
        subject=f"OpenPortfo daily update — {snapshot_date}",
        text_body=text,
        html_body=html,
    )


def run_email_job(ctx: JobContext) -> JobRun:
    started = datetime.now(timezone.utc)
    run_id = str(uuid4())
    today = ict_today()
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    def persist(
        *,
        status: str,
        message: str | None,
        counts: dict[str, object],
    ) -> JobRun:
        run = JobRun(
            run_id=run_id,
            job_type="email",
            status=status,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            message=message,
            counts=counts,
        )
        ctx.job_runs_repo.put(run)
        return run

    empty: dict[str, object] = {
        "users": 0,
        "users_total": 0,
        "users_attempted": 0,
        "users_succeeded": 0,
        "users_failed": 0,
        "sent": 0,
        "skipped_opt_out": 0,
        "skipped_no_email": 0,
        "skipped_no_snapshot": 0,
        "first_snapshot": 0,
        "news_attached": 0,
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "date": today,
    }

    try:
        settings = ctx.settings_repo.get()
        if not settings.jobs_email or not settings.email_enabled:
            reason = "jobs.email disabled" if not settings.jobs_email else "emailEnabled is false"
            return persist(status="skipped", message=reason, counts=empty)

        fallback_ccy = settings.default_display_currency or "USD"
        users_total = 0
        attempted = 0
        sent = 0
        failed = 0
        skipped_opt_out = 0
        skipped_no_email = 0
        skipped_no_snapshot = 0
        first_snapshot = 0
        news_attached = 0
        failures: list[str] = []

        for profile in _iter_profiles(ctx):
            users_total += 1
            user_id = str(profile.user_id)
            label = sanitize_error(user_id, limit=80)
            if not profile.email_opt_in:
                skipped_opt_out += 1
                continue
            if not _valid_email(profile.email):
                skipped_no_email += 1
                continue
            today_snap = ctx.snapshot_repo.get(user_id, today)
            if today_snap is None:
                skipped_no_snapshot += 1
                continue
            attempted += 1
            try:
                y_snap = ctx.snapshot_repo.get(user_id, yesterday)
                if y_snap is None:
                    first_snapshot += 1
                news, needles = related_news(ctx, user_id)
                if news:
                    news_attached += 1
                message = render_email(
                    profile=profile,
                    today=today_snap,
                    yesterday=y_snap,
                    news=news,
                    needles=needles,
                    fallback_currency=fallback_ccy,
                )
                ctx.email_sender.send(message)
                sent += 1
            except EmailSendError as exc:
                failed += 1
                if len(failures) < MAX_ERROR_DETAILS:
                    failures.append(f"user {label}: {sanitize_error(exc)}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                if len(failures) < MAX_ERROR_DETAILS:
                    failures.append(f"user {label}: {sanitize_error(exc)}")

        status = aggregate_status(attempted, failed)
        message = None
        if failures:
            message = sanitize_error(
                f"{failed} of {attempted} email users failed: {error_summary(failures)}",
                limit=MAX_ERROR_SUMMARY_LENGTH,
            )
        return persist(
            status=status,
            message=message,
            counts={
                "users": sent,
                "users_total": users_total,
                "users_attempted": attempted,
                "users_succeeded": sent,
                "users_failed": failed,
                "sent": sent,
                "skipped_opt_out": skipped_opt_out,
                "skipped_no_email": skipped_no_email,
                "skipped_no_snapshot": skipped_no_snapshot,
                "first_snapshot": first_snapshot,
                "news_attached": news_attached,
                "attempted": attempted,
                "succeeded": sent,
                "failed": failed,
                "date": today,
            },
        )
    except Exception as exc:
        return persist(status="error", message=sanitize_error(exc), counts={**empty, "failed": 1})


__all__ = ["MAX_HOLDING_ROWS", "MAX_NEWS_ITEMS", "related_news", "render_email", "run_email_job"]
