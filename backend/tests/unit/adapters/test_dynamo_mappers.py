"""Pure Dynamo item mappers — no AWS credentials required."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.adapters.dynamodb.fx import FX_PK, FX_SK, item_to_rates, rates_to_item
from app.adapters.dynamodb.holdings import holding_sk, holding_to_item, item_to_holding
from app.adapters.dynamodb.job_runs import job_pk, job_to_item, item_to_job
from app.adapters.dynamodb.news import news_pk, news_sk, news_to_item, item_to_news
from app.adapters.dynamodb.price_cache import cache_pk, cached_to_item, item_to_cached
from app.adapters.dynamodb.settings import SETTINGS_PK, SETTINGS_SK, item_to_settings, settings_to_item
from app.adapters.dynamodb.snapshots import item_to_snapshot, snapshot_sk, snapshot_to_item
from app.adapters.dynamodb.users import item_to_profile, profile_to_item
from app.adapters.dynamodb.watchlist import item_to_watch, watch_sk, watch_to_item
from app.ports.admin import JobRun, SystemSettings
from app.ports.fx import StoredRates
from app.ports.holdings import HoldingRecord
from app.ports.news import NewsItem
from app.ports.price_cache import CachedPrice
from app.ports.snapshots import SnapshotRecord
from app.ports.users import UserProfile
from app.ports.watchlist import WatchlistItem


def test_holding_sk_and_roundtrip() -> None:
    assert holding_sk("crypto", "btc") == "HOLD#crypto#BTC"
    h = HoldingRecord(
        user_id="u1",
        asset_type="crypto",
        symbol="btc",
        qty=Decimal("1.5"),
        avg_cost=Decimal("100.25"),
        currency="USD",
        asset_id="bitcoin",
        note="n",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    item = holding_to_item(h)
    assert item["sk"] == "HOLD#crypto#BTC"
    assert isinstance(item["qty"], Decimal)
    back = item_to_holding(item)
    assert back.user_id == "u1"
    assert back.symbol == "BTC"
    assert back.qty == Decimal("1.5")
    assert back.avg_cost == Decimal("100.25")


def test_watch_sk_roundtrip() -> None:
    assert watch_sk("stock", "vnm") == "WATCH#stock#VNM"
    w = WatchlistItem(
        user_id="u1",
        asset_type="stock",
        symbol="vnm",
        asset_id="VNM",
        added_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    back = item_to_watch(watch_to_item(w))
    assert back.sk == "WATCH#stock#VNM"
    assert back.symbol == "VNM"


def test_user_profile_roundtrip() -> None:
    p = UserProfile(
        user_id="sub-1",
        email="a@b.com",
        name="A",
        role="admin",
        news_keywords=["btc", "vnm"],
        email_opt_in=True,
        preferred_currency="VND",
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    back = item_to_profile(profile_to_item(p))
    assert back.user_id == "sub-1"
    assert back.role == "admin"
    assert back.news_keywords == ["btc", "vnm"]
    assert back.preferred_currency == "VND"

    unset = UserProfile(user_id="sub-2")
    unset_item = profile_to_item(unset)
    assert not unset_item.get("preferredCurrency")
    assert not item_to_profile(unset_item).preferred_currency
    assert not item_to_profile({"userId": "sub-2", "preferredCurrency": ""}).preferred_currency


def test_price_cache_pk_and_roundtrip() -> None:
    assert cache_pk("crypto", "btc") == "crypto#BTC"
    c = CachedPrice(
        asset_type="crypto",
        symbol="BTC",
        price=Decimal("65000"),
        currency="USD",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        expires_at=datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc),
    )
    item = cached_to_item(c)
    assert item["pk"] == "crypto#BTC"
    assert "ttl" in item
    back = item_to_cached(item)
    assert back.price == Decimal("65000")
    assert back.is_fresh(datetime(2026, 4, 1, 0, 30, tzinfo=timezone.utc))


def test_settings_singleton_keys() -> None:
    s = SystemSettings(email_time="09:30", jobs_news=False)
    item = settings_to_item(s)
    assert item["pk"] == SETTINGS_PK == "SETTINGS"
    assert item["sk"] == SETTINGS_SK == "GLOBAL"
    back = item_to_settings(item)
    assert back.email_time == "09:30"
    assert back.jobs_news is False
    assert item_to_settings(None).jobs_snapshot is True


def test_fx_latest_keys() -> None:
    stored = StoredRates(
        base="USD",
        rates={"USD_VND": Decimal("25000"), "VND_USD": Decimal("0.00004")},
        as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
        provider="exchangerate-api",
        status="fresh",
        last_refresh_status="success",
    )
    item = rates_to_item(stored)
    assert item["pk"] == FX_PK
    assert item["sk"] == FX_SK
    back = item_to_rates(item)
    assert back is not None
    assert back.rates["USD_VND"] == Decimal("25000")


def test_news_keys_roundtrip() -> None:
    n = NewsItem(
        id="abc123",
        title="BTC rises",
        url="https://example.com/1",
        source="CoinDesk",
        published_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        symbols=["BTC"],
        keywords=["btc"],
        date="2026-06-01",
    )
    item = news_to_item(n)
    assert item["pk"] == news_pk("2026-06-01") == "2026-06-01"
    assert item["sk"] == news_sk("CoinDesk", "abc123")
    back = item_to_news(item)
    assert back.id == "abc123"
    assert back.title == "BTC rises"


def test_job_run_and_snapshot_keys() -> None:
    run = JobRun(
        run_id="r1",
        job_type="news",
        status="success",
        started_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 1, 0, 1, tzinfo=timezone.utc),
        message=None,
        counts={"written": 2},
    )
    item = job_to_item(run)
    assert item["pk"] == job_pk("news") == "JOB#news"
    back = item_to_job(item)
    assert back.run_id == "r1"
    assert back.counts["written"] == 2

    assert snapshot_sk("2026-08-09") == "SNAP#2026-08-09"
    snap = SnapshotRecord(
        user_id="u1",
        date="2026-08-09",
        payload={"userId": "u1", "totalsByCurrency": {"USD": {"pnl": "1"}}},
        created_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
    )
    s_item = snapshot_to_item(snap)
    assert s_item["sk"] == "SNAP#2026-08-09"
    s_back = item_to_snapshot(s_item)
    assert s_back.date == "2026-08-09"
    assert s_back.payload["userId"] == "u1"


def test_aws_adapters_flag_defaults_off() -> None:
    from app.core.config import Settings, clear_settings_cache

    clear_settings_cache()
    s = Settings()
    assert s.storage_backend == "memory"
    assert s.use_aws_adapters is False
    assert s.aws_adapters_enabled() is False
    assert s.auth_mode == "fake"
