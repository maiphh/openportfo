"""Sprint 07: history cache-aside API."""

from __future__ import annotations

from datetime import datetime, timezone
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
