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
from app.ports.watchlist import WatchlistItem
from app.services.market_service import MarketService, QuoteKey
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


def test_news_job_skips_write_when_no_needles() -> None:
    url = "https://example.com/feed.xml"
    fetcher = FakeRssFetcher(
        {url: [RssItem(title="Bitcoin hits ATH", url="https://ex/btc")]}
    )
    ctx, bag = _ctx(rss_fetcher=fetcher)
    bag["rss_repo"].create(
        RssSource(source_id="s1", name="Ex", url=url, enabled=True)
    )
    bag["users"].get_or_create("u1", email="u@t.com", name="U")

    run = run_news_job(ctx)
    assert run.status == "success"
    assert run.counts["written"] == 0
    assert bag["news"].list_recent(10) == []


def test_news_job_matches_holding_symbol() -> None:
    url = "https://example.com/feed.xml"
    fetcher = FakeRssFetcher(
        {
            url: [
                RssItem(title="ETH rally continues", url="https://ex/eth"),
                RssItem(title="Weather today", url="https://ex/wx"),
            ]
        }
    )
    ctx, bag = _ctx(rss_fetcher=fetcher)
    bag["rss_repo"].create(
        RssSource(source_id="s1", name="Ex", url=url, enabled=True)
    )
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
    bag["holdings"].create(
        HoldingRecord(
            user_id="u1",
            asset_type="crypto",
            symbol="ETH",
            qty=Decimal("1"),
            avg_cost=Decimal("1000"),
            currency="USD",
            asset_id="ethereum",
        )
    )

    run = run_news_job(ctx)
    assert run.status == "success"
    assert run.counts["written"] == 1
    items = bag["news"].list_recent(10)
    assert len(items) == 1
    assert "ETH" in items[0].title


def test_price_job_disabled_skips() -> None:
    settings = SystemSettings(jobs_price=False)
    ctx, bag = _ctx(settings=settings)
    run = run_price_job(ctx)
    assert run.status == "skipped"
    assert "disabled" in (run.message or "")
    assert bag["job_runs"].list_recent(job_type="price")[0].status == "skipped"


class _RaisingRss:
    def fetch(self, url: str) -> list[RssItem]:
        raise RuntimeError("rss down")


class _SelectiveRss:
    def __init__(self, items: dict[str, list[RssItem]], failing: set[str]) -> None:
        self.items = items
        self.failing = failing
        self.fetch_calls: list[str] = []

    def fetch(self, url: str) -> list[RssItem]:
        self.fetch_calls.append(url)
        if url in self.failing:
            raise RuntimeError("source unavailable\nprovider detail")
        return list(self.items.get(url, []))


class _RaisingMarket:
    def get_quotes(self, keys: Any, force: bool = False) -> list[Any]:
        raise RuntimeError("market down")


class _SelectiveBatchMarket:
    def __init__(self, failing_call: int) -> None:
        self.failing_call = failing_call
        self.calls: list[list[QuoteKey]] = []

    def get_quotes(self, keys: Any, force: bool = False) -> list[PriceQuote]:
        batch = list(keys)
        self.calls.append(batch)
        if len(self.calls) == self.failing_call:
            raise RuntimeError("batch unavailable")
        return [
            PriceQuote(
                asset_type=key.asset_type,
                symbol=key.symbol,
                price=Decimal("10"),
                currency="USD",
                as_of=datetime.now(timezone.utc),
            )
            for key in batch
        ]


class _RaisingStorage:
    def put_json(self, key: str, data: dict[str, Any]) -> None:
        raise RuntimeError("storage down")


class _SelectiveStorage(InMemoryObjectStorage):
    def __init__(self, failing_user: str) -> None:
        super().__init__()
        self.failing_user = failing_user

    def put_json(self, key: str, data: dict[str, Any]) -> None:
        if f"userId={self.failing_user}" in key:
            raise RuntimeError("storage unavailable\nfor user")
        super().put_json(key, data)


class _SelectiveSnapshotRepo(InMemorySnapshotRepo):
    """Fail publication for one user while allowing retries to recover."""

    def __init__(self, failing_user: str) -> None:
        super().__init__()
        self.failing_user = failing_user
        self.fail = True

    def put(self, record: Any) -> None:
        if self.fail and record.user_id == self.failing_user:
            raise RuntimeError("snapshot repository unavailable")
        super().put(record)


def test_job_records_error_when_dependency_raises() -> None:
    url = "https://example.com/feed.xml"
    ctx, bag = _ctx(rss_fetcher=_RaisingRss())  # type: ignore[arg-type]
    bag["rss_repo"].create(
        RssSource(source_id="s1", name="Ex", url=url, enabled=True)
    )
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
    bag["users"].update_settings("u1", news_keywords=["bitcoin"])

    news_run = run_news_job(ctx)
    assert news_run.status == "error"
    assert "rss down" in (news_run.message or "")
    assert bag["job_runs"].list_recent(job_type="news")[0].status == "error"

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
    ctx.market_service = _RaisingMarket()  # type: ignore[assignment]
    price_run = run_price_job(ctx)
    assert price_run.status == "error"
    assert "market down" in (price_run.message or "")
    assert bag["job_runs"].list_recent(job_type="price")[0].status == "error"

    ctx.market_service = bag["market"]
    ctx.object_storage = _RaisingStorage()  # type: ignore[assignment]
    snap_run = run_snapshot_job(ctx)
    assert snap_run.status == "error"
    assert "storage down" in (snap_run.message or "")
    assert bag["job_runs"].list_recent(job_type="snapshot")[0].status == "error"

    ctx.market_service = _RaisingMarket()  # type: ignore[assignment]
    out = handler({"job": "price"}, ctx)
    assert out["status"] == "error"
    assert "market down" in (out["message"] or "")


def test_news_job_isolates_sources_and_persists_one_partial_run() -> None:
    good_url = "https://example.com/good.xml"
    bad_url = "https://example.com/bad.xml"
    fetcher = _SelectiveRss(
        {good_url: [RssItem(title="Bitcoin recovers", url="https://ex/btc")]},
        {bad_url},
    )
    ctx, bag = _ctx(rss_fetcher=fetcher)  # type: ignore[arg-type]
    bag["rss_repo"].create(
        RssSource(source_id="good", name="Good", url=good_url, enabled=True)
    )
    bag["rss_repo"].create(
        RssSource(source_id="bad", name="Bad", url=bad_url, enabled=True)
    )
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
    bag["users"].update_settings("u1", news_keywords=["bitcoin"])

    run = run_news_job(ctx)

    assert run.status == "partial"
    assert run.counts["sources_attempted"] == 2
    assert run.counts["sources_succeeded"] == 1
    assert run.counts["sources_failed"] == 1
    assert run.counts["fetched"] == 1
    assert run.counts["written"] == 1
    assert len(fetcher.fetch_calls) == 2
    assert len(bag["job_runs"].list_recent(job_type="news")) == 1
    assert "provider detail" in (run.message or "")
    assert "\n" not in (run.message or "")


def test_price_job_isolates_bounded_batches() -> None:
    ctx, bag = _ctx()
    bag["users"].get_or_create("u1", email="u@t.com", name="U")
    for symbol in ("AAA", "BBB", "CCC"):
        bag["holdings"].create(
            HoldingRecord(
                user_id="u1",
                asset_type="stock",
                symbol=symbol,
                qty=Decimal("1"),
                avg_cost=Decimal("1"),
                currency="USD",
            )
        )
    market = _SelectiveBatchMarket(failing_call=2)
    ctx.market_service = market  # type: ignore[assignment]

    run = run_price_job(ctx, batch_size=1)

    assert run.status == "partial"
    assert run.counts["symbols"] == 3
    assert run.counts["batches"] == 3
    assert run.counts["batches_attempted"] == 3
    assert run.counts["batches_succeeded"] == 2
    assert run.counts["batches_failed"] == 1
    assert run.counts["quotes"] == 2
    assert len(market.calls) == 3
    assert len(bag["job_runs"].list_recent(job_type="price")) == 1


class _RecordingMarket:
    def __init__(self) -> None:
        self.calls: list[list[QuoteKey]] = []

    def get_quotes(self, keys: Any, force: bool = False) -> list[PriceQuote]:
        batch = list(keys)
        self.calls.append(batch)
        return [
            PriceQuote(
                asset_type=key.asset_type,
                symbol=key.symbol,
                price=Decimal("10"),
                currency="USD",
                as_of=datetime.now(timezone.utc),
            )
            for key in batch
        ]


def test_price_job_streams_deduplicated_symbols_with_bounded_requests() -> None:
    ctx, bag = _ctx()
    bag["users"].get_or_create("u1", email="u1@example.com", name="U1")
    for symbol in ("AAA", "BBB"):
        bag["holdings"].create(
            HoldingRecord(
                user_id="u1",
                asset_type="stock",
                symbol=symbol,
                qty=Decimal("1"),
                avg_cost=Decimal("1"),
                currency="VND",
            )
        )
    # BBB is already held; only CCC should be added from the watchlist.
    bag["watchlist"].add(
        WatchlistItem(user_id="u1", asset_type="stock", symbol="BBB")
    )
    bag["watchlist"].add(
        WatchlistItem(user_id="u1", asset_type="stock", symbol="CCC")
    )
    # This user has holdings but no profile and must still be traversed.
    bag["holdings"].create(
        HoldingRecord(
            user_id="orphan-user",
            asset_type="stock",
            symbol="DDD",
            qty=Decimal("1"),
            avg_cost=Decimal("1"),
            currency="VND",
        )
    )

    market = _RecordingMarket()
    ctx.market_service = market  # type: ignore[assignment]
    run = run_price_job(ctx, batch_size=2)

    assert run.status == "success"
    assert run.counts["symbols"] == 4
    assert run.counts["batches"] == 2
    assert all(len(batch) <= 2 for batch in market.calls)
    requested = [key.symbol for batch in market.calls for key in batch]
    assert requested == ["AAA", "BBB", "CCC", "DDD"]


def test_snapshot_job_isolates_users_and_persists_one_partial_run() -> None:
    ctx, bag = _ctx()
    for user_id in ("u1", "u2"):
        bag["users"].get_or_create(user_id, email=f"{user_id}@t.com", name=user_id)
        bag["holdings"].create(
            HoldingRecord(
                user_id=user_id,
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
            as_of=datetime.now(timezone.utc),
        ),
        ttl_seconds=600,
    )
    ctx.object_storage = _SelectiveStorage("u1")  # type: ignore[assignment]

    run = run_snapshot_job(ctx)

    assert run.status == "partial"
    assert run.counts["users"] == 1
    assert run.counts["users_attempted"] == 2
    assert run.counts["users_succeeded"] == 1
    assert run.counts["users_failed"] == 1
    assert len(bag["job_runs"].list_recent(job_type="snapshot")) == 1
    date = run.counts["date"]
    # Storage is the first publication step.  A failed upload must not leave
    # an API-visible repository row behind.
    assert bag["snaps"].get("u1", date) is None
    assert bag["snaps"].get("u2", date) is not None
    assert ctx.object_storage.get_json(snapshot_storage_key("u1", date)) is None
    assert ctx.object_storage.get_json(snapshot_storage_key("u2", date)) is not None
    assert "\n" not in (run.message or "")


def test_snapshot_repo_failure_leaves_retry_safe_object_and_other_users_continue() -> None:
    ctx, bag = _ctx()
    for user_id in ("u1", "u2"):
        bag["users"].get_or_create(user_id, email=f"{user_id}@t.com", name=user_id)
        bag["holdings"].create(
            HoldingRecord(
                user_id=user_id,
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
            as_of=datetime.now(timezone.utc),
        ),
        ttl_seconds=600,
    )

    snapshots = _SelectiveSnapshotRepo("u1")
    ctx.snapshot_repo = snapshots
    first = run_snapshot_job(ctx)

    assert first.status == "partial"
    date = first.counts["date"]
    u1_key = snapshot_storage_key("u1", date)
    u2_key = snapshot_storage_key("u2", date)
    # The failed DDB write leaves only an unreferenced, deterministic object.
    assert ctx.object_storage.get_json(u1_key) is not None
    assert snapshots.get("u1", date) is None
    assert snapshots.get("u2", date) is not None
    assert ctx.object_storage.get_json(u2_key) is not None
    assert snapshots.get("u2", date).payload == ctx.object_storage.get_json(u2_key)

    # A retry on the same date converges to one object and one upserted row.
    snapshots.fail = False
    second = run_snapshot_job(ctx)

    assert second.status == "success"
    assert second.counts["date"] == date
    assert snapshots.get("u1", date) is not None
    assert snapshots.get("u2", date) is not None
    assert ctx.object_storage.list_keys(prefix="snapshots/userId=u1/") == [u1_key]
    assert ctx.object_storage.list_keys(prefix="snapshots/userId=u2/") == [u2_key]
