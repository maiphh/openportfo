"""BL-032 daily email job."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.jobs.email_job import run_email_job
from app.jobs.handler import handler
from app.jobs.job_utils import ict_today
from app.ports.admin import SystemSettings
from app.ports.holdings import HoldingRecord
from app.ports.news import NewsItem
from app.ports.snapshots import SnapshotRecord
from app.ports.users import UserSettingsPatch
from app.ports.watchlist import WatchlistItem
from tests.unit.jobs.test_jobs import _ctx


def _enable_email(bag: dict) -> None:
    bag["settings_repo"].save(
        SystemSettings(jobs_email=True, email_enabled=True, jobs_snapshot=True)
    )


def _opt_in(bag: dict, user_id: str = "u1", email: str = "u@t.com") -> None:
    bag["users"].get_or_create(user_id, email=email, name="U")
    bag["users"].update_settings(user_id, UserSettingsPatch(email_opt_in=True))


def _snapshot(
    bag: dict,
    user_id: str,
    day: str,
    *,
    value: str,
    cost: str,
    pnl: str,
    symbol: str = "BTC",
) -> None:
    payload = {
        "userId": user_id,
        "date": day,
        "lines": [
            {
                "symbol": symbol,
                "assetType": "crypto",
                "qty": "1",
                "currency": "USD",
                "marketValue": value,
                "costBasis": cost,
                "pnl": pnl,
                "missingPrice": False,
            }
        ],
        "totalsByCurrency": {
            "USD": {"marketValue": value, "costBasis": cost, "pnl": pnl},
        },
    }
    bag["snaps"].put(
        SnapshotRecord(
            user_id=user_id,
            date=day,
            payload=payload,
            created_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        )
    )


def test_email_job_sends_opt_in_user_with_pnl_and_holdings(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.email_job.ict_today", lambda: "2026-09-13")
    ctx, bag = _ctx()
    _enable_email(bag)
    _opt_in(bag)
    bag["holdings"].create(
        HoldingRecord(
            user_id="u1",
            asset_type="crypto",
            symbol="BTC",
            qty=Decimal("1"),
            avg_cost=Decimal("30000"),
            currency="USD",
            asset_id="bitcoin",
        )
    )
    _snapshot(bag, "u1", "2026-09-13", value="65000", cost="30000", pnl="35000")
    _snapshot(bag, "u1", "2026-09-12", value="60000", cost="30000", pnl="30000")
    bag["users"].get_or_create("u2", email="skip@t.com", name="Skip")
    _snapshot(bag, "u2", "2026-09-13", value="1", cost="1", pnl="0")

    out = handler({"job": "email"}, ctx)
    assert out["status"] == "success"
    assert out["counts"]["sent"] == 1
    assert out["counts"]["skipped_opt_out"] == 1
    assert len(bag["email"].sent) == 1
    body = bag["email"].sent[0].text_body
    assert "PnL vs cost" in body
    assert "35000" in body.replace(",", "")
    assert "BTC" in body
    assert "Holdings" in body
    assert bag["email"].sent[0].subject == "OpenPortfo daily update — 2026-09-13"


def test_email_job_skips_when_flags_off() -> None:
    ctx, bag = _ctx()
    _opt_in(bag)
    _snapshot(bag, "u1", ict_today(), value="1", cost="1", pnl="0")
    run = run_email_job(ctx)
    assert run.status == "skipped"
    assert bag["email"].sent == []


def test_email_job_skips_missing_today_snapshot(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.email_job.ict_today", lambda: "2026-09-13")
    ctx, bag = _ctx()
    _enable_email(bag)
    _opt_in(bag)
    run = run_email_job(ctx)
    assert run.status == "success"
    assert run.counts["skipped_no_snapshot"] == 1
    assert bag["email"].sent == []


def test_email_job_news_matches_holdings_and_watchlist_only(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.email_job.ict_today", lambda: "2026-09-13")
    ctx, bag = _ctx()
    _enable_email(bag)
    _opt_in(bag)
    bag["holdings"].create(
        HoldingRecord(
            user_id="u1",
            asset_type="crypto",
            symbol="BTC",
            qty=Decimal("1"),
            avg_cost=Decimal("1"),
            currency="USD",
            asset_id="bitcoin",
        )
    )
    bag["watchlist"].add(
        WatchlistItem(user_id="u1", asset_type="stock", symbol="VNM", asset_id="VNM")
    )
    bag["users"].update_settings("u1", UserSettingsPatch(news_keywords=["secret-kw"]))
    _snapshot(bag, "u1", "2026-09-13", value="2", cost="1", pnl="1")
    bag["news"].seed(
        [
            NewsItem(
                id="btc",
                title="BTC rallies overnight",
                url="https://ex/btc",
                source="Wire",
                symbols=["BTC"],
                date="2026-09-13",
            ),
            NewsItem(
                id="vnm",
                title="Vinamilk VNM outlook",
                url="https://ex/vnm",
                source="CafeF",
                symbols=["VNM"],
                date="2026-09-13",
            ),
            NewsItem(
                id="kw",
                title="secret-kw only headline",
                url="https://ex/kw",
                source="X",
                symbols=[],
                date="2026-09-13",
            ),
            NewsItem(
                id="mkt",
                title="Global stock markets jump",
                url="https://ex/mkt",
                source="Mkt",
                symbols=[],
                date="2026-09-13",
            ),
        ]
    )
    run = run_email_job(ctx)
    assert run.status == "success"
    body = bag["email"].sent[0].text_body
    assert "BTC rallies overnight" in body
    assert "Vinamilk VNM outlook" in body
    assert "secret-kw only headline" not in body
    assert "Global stock markets jump" not in body


def test_email_job_empty_news_still_sends(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.email_job.ict_today", lambda: "2026-09-13")
    ctx, bag = _ctx()
    _enable_email(bag)
    _opt_in(bag)
    _snapshot(bag, "u1", "2026-09-13", value="2", cost="1", pnl="1")
    run = run_email_job(ctx)
    assert run.status == "success"
    assert run.counts["sent"] == 1
    assert "No related news today." in bag["email"].sent[0].text_body
