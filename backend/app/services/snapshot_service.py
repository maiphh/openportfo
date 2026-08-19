"""Read user portfolio snapshots and derive performance series."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from app.ports.snapshots import SnapshotRecord, SnapshotRepo

VALID_PERF_RANGES = frozenset({"1d", "1w", "mtd", "ytd", "max"})


class SnapshotValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def parse_iso_date(value: str, *, field: str) -> str:
    raw = (value or "").strip()
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise SnapshotValidationError(f"{field} must be YYYY-MM-DD") from exc
    return parsed.isoformat()


def range_start(range_: str, today: date) -> Optional[date]:
    key = (range_ or "").strip().lower()
    if key not in VALID_PERF_RANGES:
        raise SnapshotValidationError("range must be one of 1d, 1w, mtd, ytd, max")
    if key == "1d":
        return today - timedelta(days=1)
    if key == "1w":
        return today - timedelta(days=7)
    if key == "mtd":
        return today.replace(day=1)
    if key == "ytd":
        return today.replace(month=1, day=1)
    return None


def snapshot_market_value(payload: dict[str, Any]) -> tuple[Optional[Decimal], Optional[str]]:
    """Prefer totalsDisplay; else a single native currency bucket."""
    totals_display = payload.get("totalsDisplay")
    if isinstance(totals_display, dict) and totals_display.get("marketValue") is not None:
        try:
            return Decimal(str(totals_display["marketValue"])), (
                str(totals_display.get("currency") or "").upper() or None
            )
        except (InvalidOperation, ValueError):
            return None, None
    totals = payload.get("totalsByCurrency") or {}
    if isinstance(totals, dict) and len(totals) == 1:
        currency, bucket = next(iter(totals.items()))
        if isinstance(bucket, dict) and bucket.get("marketValue") is not None:
            try:
                return Decimal(str(bucket["marketValue"])), str(currency).upper()
            except (InvalidOperation, ValueError):
                return None, None
    return None, None


def record_to_dict(record: SnapshotRecord) -> dict[str, Any]:
    created = record.created_at
    created_s = None
    if created is not None:
        created_s = created.isoformat()
        if created.tzinfo is None:
            created_s += "Z"
    return {
        "userId": record.user_id,
        "date": record.date,
        "createdAt": created_s,
        "payload": record.payload or {},
    }


class SnapshotService:
    def __init__(self, repo: SnapshotRepo) -> None:
        self._repo = repo

    def get(self, user_id: str, date_s: str) -> SnapshotRecord:
        parsed = parse_iso_date(date_s, field="date")
        record = self._repo.get(user_id, parsed)
        if record is None:
            raise KeyError(parsed)
        return record

    def list(
        self,
        user_id: str,
        *,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[SnapshotRecord]:
        lo = parse_iso_date(date_from, field="from") if date_from else None
        hi = parse_iso_date(date_to, field="to") if date_to else None
        if lo and hi and lo > hi:
            raise SnapshotValidationError("from must be on or before to")
        return self._repo.list(user_id, date_from=lo, date_to=hi)

    def performance(
        self,
        user_id: str,
        *,
        range_: str,
        today: Optional[date] = None,
    ) -> dict[str, Any]:
        today_d = today or datetime.now(timezone.utc).date()
        start = range_start(range_, today_d)
        date_from = start.isoformat() if start else None
        records = self._repo.list(user_id, date_from=date_from, date_to=today_d.isoformat())
        points: list[dict[str, Any]] = []
        for record in records:
            value, currency = snapshot_market_value(record.payload or {})
            points.append(
                {
                    "date": record.date,
                    "marketValue": format(value, "f") if value is not None else None,
                    "currency": currency,
                }
            )
        last_valued = next((p for p in reversed(points) if p["marketValue"] is not None), None)
        currency = last_valued.get("currency") if last_valued else None
        same_ccy = [
            p
            for p in points
            if p["marketValue"] is not None
            and currency
            and p.get("currency") == currency
        ]
        first_valued = same_ccy[0] if same_ccy else None
        last_same = same_ccy[-1] if same_ccy else None
        change = None
        change_pct = None
        start_value = first_valued["marketValue"] if first_valued else None
        end_value = last_same["marketValue"] if last_same else None
        if (
            first_valued
            and last_same
            and first_valued["date"] != last_same["date"]
        ):
            start_v = Decimal(first_valued["marketValue"])
            end_v = Decimal(last_same["marketValue"])
            change = end_v - start_v
            if start_v != 0:
                change_pct = change / start_v
        return {
            "range": (range_ or "").strip().lower(),
            "from": date_from,
            "to": today_d.isoformat(),
            "startValue": start_value,
            "endValue": end_value,
            "change": format(change, "f") if change is not None else None,
            "changePercent": format(change_pct, "f") if change_pct is not None else None,
            "currency": currency,
            "points": points,
        }


__all__ = [
    "SnapshotService",
    "SnapshotValidationError",
    "VALID_PERF_RANGES",
    "parse_iso_date",
    "range_start",
    "snapshot_market_value",
    "record_to_dict",
]
