"""Sprint 07: history cache-aside API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.deps import (
    set_crypto_market_client,
    set_history_service,
    set_object_storage,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.main import create_app
from app.services.history_service import HistoryService, build_history_key
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.storage import InMemoryObjectStorage
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(uid: str = "u1") -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{uid}"}


def _setup(
    *,
    storage: InMemoryObjectStorage | None = None,
    crypto: FixtureCryptoMarketClient | None = None,
    stock: FixtureStockMarketClient | None = None,
) -> tuple[TestClient, InMemoryObjectStorage, FixtureCryptoMarketClient, FixtureStockMarketClient]:
    set_user_profile_repo(InMemoryUserProfileRepo())
    storage = storage or InMemoryObjectStorage()
    crypto = crypto or FixtureCryptoMarketClient()
    stock = stock or FixtureStockMarketClient()
    set_object_storage(storage)
    set_crypto_market_client(crypto)
    set_stock_market_client(stock)
    set_history_service(HistoryService(storage, crypto, stock))
    return TestClient(create_app()), storage, crypto, stock


def test_history_requires_auth() -> None:
    client, *_ = _setup()
    r = client.get("/api/assets/bitcoin/history?range=30d&type=crypto")
    assert r.status_code == 401


def test_invalid_range_400() -> None:
    client, *_ = _setup()
    r = client.get(
        "/api/assets/bitcoin/history",
        headers=_auth(),
        params={"range": "2d", "type": "crypto"},
    )
    assert r.status_code == 400


def test_miss_calls_market_and_puts() -> None:
    crypto = FixtureCryptoMarketClient()
    crypto.set_chart(
        "bitcoin",
        "7d",
        [
            {"t": datetime(2026, 8, 1, tzinfo=timezone.utc), "price": Decimal("60000")},
            {"t": datetime(2026, 8, 7, tzinfo=timezone.utc), "price": Decimal("65000")},
        ],
    )
    client, storage, crypto, _ = _setup(crypto=crypto)
    r = client.get(
        "/api/assets/bitcoin/history",
        headers=_auth(),
        params={"range": "7d", "type": "crypto"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "live"
    assert body["assetId"] == "bitcoin"
    assert len(body["points"]) >= 1
    assert crypto.chart_calls == 1
    assert storage.put_calls == 1
    assert storage.last_put_key == build_history_key("crypto", "bitcoin", "7d")


def test_hit_skips_market() -> None:
    storage = InMemoryObjectStorage()
    key = build_history_key("crypto", "bitcoin", "30d")
    storage.seed(
        key,
        {
            "assetId": "bitcoin",
            "range": "30d",
            "type": "crypto",
            "points": [{"t": "2026-08-01T00:00:00+00:00", "price": "64000"}],
            "cachedAt": "2026-08-20T00:00:00+00:00",
            "expiresAt": "2099-01-01T00:00:00+00:00",
        },
    )
    crypto = FixtureCryptoMarketClient()
    client, storage, crypto, _ = _setup(storage=storage, crypto=crypto)
    r = client.get(
        "/api/assets/bitcoin/history",
        headers=_auth(),
        params={"range": "30d", "type": "crypto"},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "cache"
    assert getattr(crypto, "chart_calls", 0) == 0
    assert storage.put_calls == 0


def test_expired_cache_refreshes_and_force_bypasses_fresh_cache() -> None:
    now = [datetime(2026, 8, 20, tzinfo=timezone.utc)]
    storage = InMemoryObjectStorage()
    crypto = FixtureCryptoMarketClient()
    stock = FixtureStockMarketClient()
    crypto.set_chart(
        "bitcoin",
        "7d",
        [{"t": now[0], "price": Decimal("65000")}],
    )
    service = HistoryService(
        storage,
        crypto,
        stock,
        ttl_seconds=60,
        clock=lambda: now[0],
    )

    first = service.get_history(asset_id="bitcoin", asset_type="crypto", range_="7d")
    assert first["source"] == "live"
    assert first["stale"] is False
    assert first["cachedAt"] == "2026-08-20T00:00:00+00:00"
    assert first["expiresAt"] == "2026-08-20T00:01:00+00:00"
    assert crypto.chart_calls == 1

    # A fresh cache is used without another provider call.
    cached = service.get_history(asset_id="bitcoin", asset_type="crypto", range_="7d")
    assert cached["source"] == "cache"
    assert crypto.chart_calls == 1

    # Once expired, the next request revalidates and writes a new expiry.
    now[0] += timedelta(seconds=61)
    crypto.set_chart(
        "bitcoin",
        "7d",
        [{"t": now[0], "price": Decimal("66000")}],
    )
    refreshed = service.get_history(asset_id="bitcoin", asset_type="crypto", range_="7d")
    assert refreshed["source"] == "live"
    assert refreshed["stale"] is False
    assert refreshed["points"][0]["price"] == "66000"
    assert refreshed["expiresAt"] == "2026-08-20T00:02:01+00:00"
    assert crypto.chart_calls == 2

    # Explicit force refresh bypasses even the newly-fresh cache.
    crypto.set_chart(
        "bitcoin",
        "7d",
        [{"t": now[0], "price": Decimal("67000")}],
    )
    forced = service.get_history(
        asset_id="bitcoin",
        asset_type="crypto",
        range_="7d",
        force=True,
    )
    assert forced["source"] == "live"
    assert forced["points"][0]["price"] == "67000"
    assert crypto.chart_calls == 3


def test_legacy_cache_is_expired_and_provider_failure_returns_stale_last_good() -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    storage = InMemoryObjectStorage()
    key = build_history_key("crypto", "bitcoin", "7d")
    storage.seed(
        key,
        {
            "assetId": "bitcoin",
            "range": "7d",
            "type": "crypto",
            "points": [{"t": "2026-08-01T00:00:00+00:00", "price": "64000"}],
        },
    )
    crypto = FixtureCryptoMarketClient()
    crypto.get_market_chart = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("down"))
    service = HistoryService(
        storage,
        crypto,
        FixtureStockMarketClient(),
        ttl_seconds=60,
        clock=lambda: now,
    )

    result = service.get_history(asset_id="bitcoin", asset_type="crypto", range_="7d")
    assert result["source"] == "cache"
    assert result["stale"] is True
    assert result["points"][0]["price"] == "64000"
    assert storage.put_calls == 0


def test_empty_market_synthesizes_without_storing_as_live() -> None:
    client, storage, crypto, _ = _setup()
    r = client.get(
        "/api/assets/bitcoin/history",
        headers=_auth(),
        params={"range": "7d", "type": "crypto"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "synthetic"
    assert body["assetId"] == "bitcoin"
    assert len(body["points"]) >= 1
    assert crypto.chart_calls == 1
    assert storage.put_calls == 0
