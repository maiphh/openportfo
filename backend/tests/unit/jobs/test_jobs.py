"""Sprint 10: Lambda-shaped jobs with fakes."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.models import PriceQuote
from app.jobs.context import JobContext
from app.jobs.handler import handler
from app.jobs.news_job import run_news_job
from app.jobs.price_job import run_price_job
from app.jobs.snapshot_job import run_snapshot_job, snapshot_storage_key
from app.ports.admin import RssSource, SystemSettings
from app.ports.holdings import HoldingRecord
from app.ports.rss import RssItem
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from tests.fakes.admin import (
    InMemoryJobRunsRepo,
    InMemoryRssSourcesRepo,
    InMemorySettingsRepo,
)
from tests.fakes.fx import FakeExchangeRateClient, InMemoryExchangeRateRepo
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.news import InMemoryNewsRepo
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.rss import FakeRssFetcher
from tests.fakes.snapshots import InMemorySnapshotRepo
from tests.fakes.storage import InMemoryObjectStorage
from tests.fakes.users import InMemoryUserProfileRepo
from tests.fakes.watchlist import InMemoryWatchlistRepo


def _ctx(
    *,
    settings: SystemSettings | None = None,
    rss_fetcher: FakeRssFetcher | None = None,
) -> tuple[JobContext, dict[str, Any]]:
    settings_repo = InMemorySettingsRepo(initial=settings or SystemSettings())
    rss_repo = InMemoryRssSourcesRepo()
    job_runs = InMemoryJobRunsRepo()
    news = InMemoryNewsRepo()
    fetcher = rss_fetcher or FakeRssFetcher()
    holdings = InMemoryHoldingsRepo()
    watchlist = InMemoryWatchlistRepo()
    cache = InMemoryPriceCacheRepo()
    crypto = FixtureCryptoMarketClient()
    stock = FixtureStockMarketClient()
    market = MarketService(crypto, stock, cache, default_ttl_seconds=600)
    fx_repo = InMemoryExchangeRateRepo()
    # ExchangeRateClient exists but must NOT be on JobContext
    _fx_client = FakeExchangeRateClient()
    portfolio = PortfolioService(holdings, market, fx_repo=fx_repo)
    snaps = InMemorySnapshotRepo()
    storage = InMemoryObjectStorage()
    users = InMemoryUserProfileRepo()

    ctx = JobContext(
        settings_repo=settings_repo,
        rss_sources_repo=rss_repo,
        job_runs_repo=job_runs,
        news_repo=news,
        rss_fetcher=fetcher,
        holdings_repo=holdings,
        watchlist_repo=watchlist,
        market_service=market,
        portfolio_service=portfolio,
        snapshot_repo=snaps,
        object_storage=storage,
        user_profile_repo=users,
        fx_repo=fx_repo,
    )
    bag = {
        "settings_repo": settings_repo,
        "rss_repo": rss_repo,
        "job_runs": job_runs,
        "news": news,
        "fetcher": fetcher,
        "holdings": holdings,
        "watchlist": watchlist,
        "cache": cache,
        "crypto": crypto,
        "stock": stock,
        "market": market,
        "fx_repo": fx_repo,
        "fx_client": _fx_client,
        "portfolio": portfolio,
        "snaps": snaps,
        "storage": storage,
        "users": users,
    }
    return ctx, bag


def test_news_job_writes_matched_items() -> None:
    url = "https://example.com/feed.xml"
    fetcher = FakeRssFetcher(
        {
            url: [
                RssItem(title="Bitcoin hits ATH", url="https://ex/btc"),
                RssItem(title="Weather today", url="https://ex/wx"),
            ]
        }
    )
    ctx, bag = _ctx(rss_fetcher=fetcher)
    bag["rss_repo"].create(
        RssSource(source_id="s1", name="Ex", url=url, enabled=True)
    )
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
    bag["users"].update_settings("u1", news_keywords=["bitcoin"])

    run = run_news_job(ctx)
    assert run.status == "success"
    assert run.counts["written"] == 1
    items = bag["news"].list_recent(10)
    assert len(items) == 1
    assert "Bitcoin" in items[0].title
    assert fetcher.fetch_calls == 1


def test_news_job_disabled_skips() -> None:
    settings = SystemSettings(jobs_news=False)
    ctx, bag = _ctx(settings=settings)
    run = run_news_job(ctx)
    assert run.status == "skipped"
    assert "disabled" in (run.message or "")
    assert bag["job_runs"].list_recent(job_type="news")[0].status == "skipped"


def test_price_job_updates_cache() -> None:
    ctx, bag = _ctx()
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
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
    run = run_price_job(ctx)
    assert run.status == "success"
    assert run.counts["symbols"] >= 1
    assert bag["crypto"].price_calls >= 1
    cached = bag["cache"].get("crypto", "BTC")
    assert cached is not None


def test_snapshot_writes_storage_and_repo() -> None:
    ctx, bag = _ctx()
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
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
    bag["cache"].put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("40000"),
            currency="USD",
            as_of=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ),
        ttl_seconds=600,
    )
    run = run_snapshot_job(ctx)
    assert run.status == "success"
    assert run.counts["users"] == 1
    date = run.counts["date"]
    assert bag["snaps"].get("u1", date) is not None
    key = snapshot_storage_key("u1", date)
    assert bag["storage"].get_json(key) is not None
    assert bag["storage"].put_calls >= 1


def test_no_exchange_rate_client_on_context() -> None:
    ctx, bag = _ctx()
    assert not hasattr(ctx, "exchange_rate_client")
    assert not hasattr(ctx, "fx_client")
    # Snapshot uses portfolio which only reads fx_repo
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
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
    bag["cache"].put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("2"),
            currency="USD",
            as_of=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ),
        ttl_seconds=600,
    )
    run_snapshot_job(ctx)
    assert bag["fx_client"].fetch_calls == 0


def test_handler_dispatches() -> None:
    ctx, bag = _ctx()
    bag["settings_repo"].save(SystemSettings(jobs_news=False))
    out = handler({"job": "news"}, ctx)
    assert out["jobType"] == "news"
    assert out["status"] == "skipped"
