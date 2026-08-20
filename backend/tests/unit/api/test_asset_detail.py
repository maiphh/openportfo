"""Asset detail page APIs: profile, quote, history, FX display."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.deps import (
    get_asset_detail_service,
    get_crypto_market_client,
    get_exchange_rate_repo,
    get_history_service,
    get_market_service,
    get_object_storage,
    get_stock_market_client,
    get_user_profile_repo,
    set_asset_detail_service,
    set_crypto_market_client,
    set_exchange_rate_repo,
    set_history_service,
    set_market_service,
    set_object_storage,
    set_price_cache_repo,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.main import create_app
from app.ports.fx import StoredRates
from app.ports.market import AssetSearchResult, MarketDataError
from app.services.asset_detail_service import AssetDetailService
from app.services.history_service import HistoryService
from app.services.market_service import MarketService
from tests.fakes.fx import InMemoryExchangeRateRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.storage import InMemoryObjectStorage
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(user_id: str = "alice") -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _make(
    *,
    fx: InMemoryExchangeRateRepo | None = None,
    crypto: FixtureCryptoMarketClient | None = None,
    stock: FixtureStockMarketClient | None = None,
    storage: InMemoryObjectStorage | None = None,
) -> tuple[TestClient, FixtureCryptoMarketClient, FixtureStockMarketClient, InMemoryObjectStorage]:
    c = crypto or FixtureCryptoMarketClient()
    s = stock or FixtureStockMarketClient()
    cache = InMemoryPriceCacheRepo()
    store = storage or InMemoryObjectStorage()
    fx_repo = fx if fx is not None else InMemoryExchangeRateRepo()
    users = InMemoryUserProfileRepo()
    market = MarketService(c, s, cache, default_ttl_seconds=600)
    history = HistoryService(store, c, s)
    detail = AssetDetailService(market, history, c, s, store, fx_repo=fx_repo)
    set_crypto_market_client(c)
    set_stock_market_client(s)
    set_price_cache_repo(cache)
    set_object_storage(store)
    set_exchange_rate_repo(fx_repo)
    set_user_profile_repo(users)
    set_market_service(market)
    set_history_service(history)
    set_asset_detail_service(detail)
    app = create_app()
    app.dependency_overrides[get_crypto_market_client] = lambda: c
    app.dependency_overrides[get_stock_market_client] = lambda: s
    app.dependency_overrides[get_object_storage] = lambda: store
    app.dependency_overrides[get_exchange_rate_repo] = lambda: fx_repo
    app.dependency_overrides[get_user_profile_repo] = lambda: users
    app.dependency_overrides[get_market_service] = lambda: market
    app.dependency_overrides[get_history_service] = lambda: history
    app.dependency_overrides[get_asset_detail_service] = lambda: detail
    return TestClient(app), c, s, store


@pytest.fixture(autouse=True)
def _reset() -> Any:
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_object_storage(None)
    set_exchange_rate_repo(None)
    set_user_profile_repo(None)
    set_market_service(None)
    set_history_service(None)
    set_asset_detail_service(None)
    yield
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_object_storage(None)
    set_exchange_rate_repo(None)
    set_user_profile_repo(None)
    set_market_service(None)
    set_history_service(None)
    set_asset_detail_service(None)


def test_detail_requires_auth() -> None:
    client, *_ = _make()
    assert client.get("/api/assets/crypto/btc").status_code == 401


def test_crypto_btc_profile_and_quote() -> None:
    client, crypto, _, _ = _make()
    r = client.get("/api/assets/crypto/btc", headers=_auth())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assetType"] == "crypto"
    assert body["symbol"] == "BTC"
    assert body["assetId"] == "bitcoin"
    assert body["name"] == "Bitcoin"
    assert body["nativeCurrency"] == "USD"
    assert body["displayCurrency"] == "USD"
    assert "decentralized" in (body["profile"]["description"] or "").lower()
    assert body["profile"]["homepage"] == "https://bitcoin.org"
    assert body["profile"]["imageUrl"]
    assert body["quote"]["price"] == "65000"
    assert body["quote"]["currency"] == "USD"
    assert body["quote"]["priceDisplay"] == "65000"
    assert body["history"] is None
    assert crypto.profile_calls == 1


def test_crypto_slug_bitcoin_and_profile_cache() -> None:
    client, crypto, _, storage = _make()
    first = client.get("/api/assets/crypto/bitcoin", headers=_auth())
    assert first.status_code == 200
    assert first.json()["symbol"] == "BTC"
    assert crypto.profile_calls == 1
    assert crypto.search_calls == 0
    second = client.get("/api/assets/crypto/bitcoin", headers=_auth())
    assert second.status_code == 200
    assert crypto.profile_calls == 1
    assert crypto.search_calls == 0
    via_ticker = client.get("/api/assets/crypto/btc", headers=_auth())
    assert via_ticker.status_code == 200
    assert via_ticker.json()["assetId"] == "bitcoin"
    assert crypto.profile_calls == 1
    assert crypto.search_calls == 0
    assert storage.get_json("profile/crypto/bitcoin.json") is not None
    assert storage.get_json("resolve/crypto/bitcoin.json") is not None
    assert storage.get_json("resolve/crypto/btc.json") is not None


def test_crypto_provider_id_resolves_outside_browse_cap() -> None:
    class SlugBlindCappedCryptoClient(FixtureCryptoMarketClient):
        def search(self, q: str) -> list[AssetSearchResult]:
            self.search_calls += 1
            return []

        def list_all(self, *, limit: int = 250) -> list[AssetSearchResult]:
            return super().list_all(limit=min(limit, 250))

    catalog = [
        AssetSearchResult(
            symbol=f"C{i}",
            name=f"Coin {i}",
            asset_id=f"coin-{i}",
            asset_type="crypto",
            currency="USD",
        )
        for i in range(291)
    ]
    catalog.append(
        AssetSearchResult(
            symbol="BOME",
            name="BOOK OF MEME",
            asset_id="book-of-meme",
            asset_type="crypto",
            currency="USD",
        )
    )
    crypto = SlugBlindCappedCryptoClient(
        search_index=catalog,
        prices={"book-of-meme": (Decimal("0.00123"), "USD")},
    )
    client, _, _, storage = _make(crypto=crypto)

    response = client.get("/api/assets/crypto/book-of-meme", headers=_auth())

    assert response.status_code == 200, response.text
    assert response.json()["assetId"] == "book-of-meme"
    assert response.json()["symbol"] == "BOME"
    assert response.json()["quote"]["price"] == "0.00123"
    assert crypto.profile_calls == 1
    assert crypto.search_calls == 0
    assert storage.get_json("resolve/crypto/book-of-meme.json") is not None
    assert storage.get_json("resolve/crypto/bome.json") is not None
    assert storage.get_json("profile/crypto/book-of-meme.json") is not None


def test_crypto_symbol_falls_back_to_search_when_not_a_provider_id() -> None:
    class IdOnlyProfileCryptoClient(FixtureCryptoMarketClient):
        def get_profile(self, id: str):
            if id.lower() == "btc":
                self.profile_calls = getattr(self, "profile_calls", 0) + 1
                self.last_profile_id = id
                raise MarketDataError("CoinGecko HTTP 404")
            return super().get_profile(id)

    crypto = IdOnlyProfileCryptoClient()
    client, _, _, _ = _make(crypto=crypto)

    response = client.get("/api/assets/crypto/btc", headers=_auth())

    assert response.status_code == 200, response.text
    assert response.json()["assetId"] == "bitcoin"
    assert response.json()["symbol"] == "BTC"
    assert crypto.search_calls == 1
    assert crypto.profile_calls == 2


def test_stock_vnm_profile() -> None:
    client, *_ = _make()
    r = client.get("/api/assets/stock/vnm", headers=_auth())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["symbol"] == "VNM"
    assert body["assetId"] == "VNM"
    assert body["nativeCurrency"] == "VND"
    assert body["profile"]["exchange"] == "HOSE"
    assert body["profile"]["industry"] == "Food & Beverage"
    assert body["quote"]["price"] == "65000"
    assert body["quote"]["currency"] == "VND"


def test_detail_currency_vnd_uses_stored_fx() -> None:
    fx = InMemoryExchangeRateRepo()
    fx.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=datetime(2026, 8, 19, tzinfo=timezone.utc),
            status="fresh",
            provider="seed",
        )
    )
    client, *_ = _make(fx=fx)
    r = client.get(
        "/api/assets/crypto/btc",
        params={"currency": "VND", "range": "7d"},
        headers=_auth(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["displayCurrency"] == "VND"
    assert body["fx"]["status"] == "fresh"
    assert body["fx"]["rate"] == "25000"
    assert body["quote"]["price"] == "65000"
    assert body["quote"]["priceDisplay"] == "1625000000"
    assert body["history"] is not None
    assert body["history"]["range"] == "7d"
    assert body["history"]["points"]
    assert body["history"]["points"][0]["priceDisplay"] is not None


def test_history_standalone_and_legacy_still_work() -> None:
    crypto = FixtureCryptoMarketClient()
    crypto.set_chart(
        "bitcoin",
        "30d",
        [
            {"t": datetime(2026, 8, 1, tzinfo=timezone.utc), "price": Decimal("60000")},
            {"t": datetime(2026, 8, 10, tzinfo=timezone.utc), "price": Decimal("65000")},
        ],
    )
    client, *_ = _make(crypto=crypto)
    r = client.get(
        "/api/assets/crypto/btc/history",
        params={"range": "30d", "currency": "USD"},
        headers=_auth(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assetId"] == "bitcoin"
    assert body["symbol"] == "BTC"
    assert len(body["points"]) == 2
    assert body["points"][1]["price"] == "65000"
    assert body["source"] == "live"

    legacy = client.get(
        "/api/assets/bitcoin/history",
        params={"range": "30d", "type": "crypto"},
        headers=_auth(),
    )
    assert legacy.status_code == 200
    assert legacy.json()["assetId"] == "bitcoin"


def test_unknown_slug_404_and_bad_type_400() -> None:
    client, *_ = _make()
    assert client.get("/api/assets/crypto/not-a-coin", headers=_auth()).status_code == 404
    assert client.get("/api/assets/crypto/coin", headers=_auth()).status_code == 404
    assert client.get("/api/assets/forex/usd", headers=_auth()).status_code == 400


def test_coingecko_profile_mapper() -> None:
    from app.adapters.coingecko.http_client import profile_from_coingecko

    profile = profile_from_coingecko(
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "description": {"en": "Peer-to-peer cash."},
            "image": {"large": "https://example.com/btc.png"},
            "links": {
                "homepage": ["https://bitcoin.org", ""],
                "twitter_screen_name": "bitcoin",
                "repos_url": {"github": ["https://github.com/bitcoin/bitcoin"]},
            },
            "categories": ["Cryptocurrency"],
            "market_cap_rank": 1,
            "genesis_date": "2009-01-03",
            "hashing_algorithm": "SHA-256",
            "market_data": {
                "price_change_percentage_24h": 2.5,
                "market_cap": {"usd": 1000},
                "total_volume": {"usd": 50},
                "circulating_supply": 19700000,
                "max_supply": 21000000,
            },
        }
    )
    assert profile.symbol == "BTC"
    assert profile.description == "Peer-to-peer cash."
    assert profile.links["twitter"] == "https://twitter.com/bitcoin"
    assert profile.market_cap == Decimal("1000")
    assert profile.change_percent_24h == Decimal("2.5")


def test_history_bad_range_400() -> None:
    client, *_ = _make()
    r = client.get(
        "/api/assets/crypto/btc/history",
        params={"range": "2d"},
        headers=_auth(),
    )
    assert r.status_code == 400
