"""Sprint 04: MarketService search + cache-first get_quotes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.models import PriceQuote
from app.ports.market import MarketDataError
from app.services.market_service import (
    MarketService,
    QuoteKey,
    ValidationError,
)
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo


def _svc(
    crypto: FixtureCryptoMarketClient | None = None,
    stock: FixtureStockMarketClient | None = None,
    cache: InMemoryPriceCacheRepo | None = None,
    ttl: int = 600,
) -> tuple[MarketService, FixtureCryptoMarketClient, FixtureStockMarketClient, InMemoryPriceCacheRepo]:
    c = crypto or FixtureCryptoMarketClient()
    s = stock or FixtureStockMarketClient()
    p = cache or InMemoryPriceCacheRepo()
    return MarketService(c, s, p, default_ttl_seconds=ttl), c, s, p


# ---------------------------------------------------------------------------
# 1. Fake crypto search mapping
# ---------------------------------------------------------------------------


def test_search_crypto_maps_results() -> None:
    svc, crypto, _, _ = _svc()
    results = svc.search("bit", "crypto")
    assert crypto.search_calls == 1
    assert len(results) >= 1
    btc = next(r for r in results if r.symbol == "BTC")
    assert btc.name == "Bitcoin"
    assert btc.asset_id == "bitcoin"
    assert btc.asset_type == "crypto"


def test_search_crypto_case_insensitive_type() -> None:
    svc, _, _, _ = _svc()
    results = svc.search("ETH", "CRYPTO")
    assert any(r.symbol == "ETH" for r in results)


# ---------------------------------------------------------------------------
# 2. Fake stock search
# ---------------------------------------------------------------------------


def test_search_stock_maps_results() -> None:
    svc, _, stock, _ = _svc()
    results = svc.search("vinamilk", "stock")
    assert stock.search_calls == 1
    assert len(results) == 1
    assert results[0].symbol == "VNM"
    assert results[0].name == "Vinamilk"
    assert results[0].asset_id == "VNM"
    assert results[0].asset_type == "stock"


def test_search_stock_by_ticker() -> None:
    svc, _, _, _ = _svc()
    results = svc.search("fpt", "stock")
    assert any(r.symbol == "FPT" for r in results)


def test_list_assets_stock_catalog() -> None:
    svc, _, stock, _ = _svc()
    results = svc.list_assets("stock", limit=250)
    assert len(results) > 3
    assert any(r.symbol == "VCB" for r in results)
    assert all(r.asset_type == "stock" for r in results)
    _ = stock


def test_list_assets_crypto_catalog() -> None:
    svc, _, _, _ = _svc()
    results = svc.list_assets("crypto", limit=20)
    assert len(results) == 20
    assert results[0].asset_id == "bitcoin"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_search_empty_q_raises() -> None:
    svc, _, _, _ = _svc()
    with pytest.raises(ValidationError, match="q must not be empty"):
        svc.search("", "crypto")
    with pytest.raises(ValidationError, match="q must not be empty"):
        svc.search("   ", "stock")


def test_search_invalid_type_raises() -> None:
    svc, _, _, _ = _svc()
    with pytest.raises(ValidationError, match="type must be"):
        svc.search("btc", "forex")


# ---------------------------------------------------------------------------
# 3. Cache hit → client call count 0
# ---------------------------------------------------------------------------


def test_get_quotes_cache_hit_skips_client() -> None:
    cache = InMemoryPriceCacheRepo()
    now = datetime.now(timezone.utc)
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("60000"),
            currency="USD",
            as_of=now,
        ),
        ttl_seconds=600,
    )
    svc, crypto, stock, _ = _svc(cache=cache)

    quotes = svc.get_quotes([("crypto", "BTC", "bitcoin")])
    assert len(quotes) == 1
    assert quotes[0].price == Decimal("60000")
    assert quotes[0].stale is False
    assert crypto.price_calls == 0
    assert stock.price_calls == 0
    assert cache.put_calls == 1  # only the seed put


def test_get_quotes_cache_hit_stock() -> None:
    cache = InMemoryPriceCacheRepo()
    cache.put(
        PriceQuote(
            asset_type="stock",
            symbol="VNM",
            price=Decimal("70000"),
            currency="VND",
            as_of=datetime.now(timezone.utc),
        ),
        600,
    )
    svc, crypto, stock, _ = _svc(cache=cache)
    quotes = svc.get_quotes([QuoteKey("stock", "VNM")])
    assert quotes[0].price == Decimal("70000")
    assert stock.price_calls == 0
    assert crypto.price_calls == 0


# ---------------------------------------------------------------------------
# 4. Cache miss → client called + put
# ---------------------------------------------------------------------------


def test_get_quotes_cache_miss_fetches_and_puts() -> None:
    svc, crypto, _, cache = _svc()
    quotes = svc.get_quotes([("crypto", "BTC", "bitcoin")])
    assert len(quotes) == 1
    assert quotes[0].symbol == "BTC"
    assert quotes[0].price == Decimal("65000")
    assert quotes[0].currency == "USD"
    assert crypto.price_calls == 1
    assert "bitcoin" in crypto.last_price_ids
    assert cache.put_calls == 1

    # Warm cache: second call does not hit client
    quotes2 = svc.get_quotes([("crypto", "BTC", "bitcoin")])
    assert quotes2[0].price == Decimal("65000")
    assert crypto.price_calls == 1
    assert cache.put_calls == 1


def test_get_quotes_stock_miss() -> None:
    svc, _, stock, cache = _svc()
    quotes = svc.get_quotes([("stock", "VNM")])
    assert len(quotes) == 1
    assert quotes[0].price == Decimal("65000")
    assert quotes[0].currency == "VND"
    assert stock.price_calls == 1
    assert cache.put_calls == 1


def test_get_quotes_batch_crypto() -> None:
    svc, crypto, _, cache = _svc()
    quotes = svc.get_quotes(
        [
            ("crypto", "BTC", "bitcoin"),
            ("crypto", "ETH", "ethereum"),
        ]
    )
    assert len(quotes) == 2
    assert crypto.price_calls == 1  # single batch
    assert set(crypto.last_price_ids) == {"bitcoin", "ethereum"}
    assert cache.put_calls == 2


def test_get_quotes_force_refreshes() -> None:
    svc, crypto, _, cache = _svc()
    svc.get_quotes([("crypto", "BTC", "bitcoin")])
    assert crypto.price_calls == 1
    svc.get_quotes([("crypto", "BTC", "bitcoin")], force=True)
    assert crypto.price_calls == 2
    assert cache.put_calls == 2


# ---------------------------------------------------------------------------
# External failure → stale cache
# ---------------------------------------------------------------------------


def test_get_quotes_external_failure_returns_stale() -> None:
    crypto = FixtureCryptoMarketClient()
    cache = InMemoryPriceCacheRepo()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    cache.seed(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("50000"),
            currency="USD",
            as_of=past,
        ),
        expires_at=past + timedelta(seconds=1),  # already expired
    )
    # Fresh get misses; client will fail
    crypto.fail_prices = True
    svc, _, _, _ = _svc(crypto=crypto, cache=cache)

    quotes = svc.get_quotes([("crypto", "BTC", "bitcoin")])
    assert len(quotes) == 1
    assert quotes[0].price == Decimal("50000")
    assert quotes[0].stale is True
    assert crypto.price_calls == 1


def test_get_quotes_external_failure_no_stale_raises() -> None:
    crypto = FixtureCryptoMarketClient(fail_prices=True)
    svc, _, _, _ = _svc(crypto=crypto)
    with pytest.raises(MarketDataError):
        svc.get_quotes([("crypto", "BTC", "bitcoin")])


def test_get_quotes_stock_failure_stale() -> None:
    stock = FixtureStockMarketClient()
    cache = InMemoryPriceCacheRepo()
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    cache.seed(
        PriceQuote(
            asset_type="stock",
            symbol="VNM",
            price=Decimal("60000"),
            currency="VND",
            as_of=past,
        ),
        expires_at=past,
    )
    stock.fail_prices = True
    svc, _, _, _ = _svc(stock=stock, cache=cache)
    quotes = svc.get_quotes([("stock", "VNM")])
    assert quotes[0].price == Decimal("60000")


# ---------------------------------------------------------------------------
# PriceCache TTL behaviour
# ---------------------------------------------------------------------------


def test_price_cache_expired_treated_as_miss() -> None:
    clock = {"now": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)}

    def _clock() -> datetime:
        return clock["now"]

    cache = InMemoryPriceCacheRepo(clock=_clock)
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("1"),
            currency="USD",
            as_of=clock["now"],
        ),
        ttl_seconds=60,
    )
    # Still fresh
    assert cache.get("crypto", "BTC") is not None
    # Advance past TTL
    clock["now"] = clock["now"] + timedelta(seconds=61)
    assert cache.get("crypto", "BTC") is None
    assert cache.get("crypto", "BTC", allow_expired=True) is not None


def test_get_quotes_empty_keys() -> None:
    svc, crypto, _, _ = _svc()
    assert svc.get_quotes([]) == []
    assert crypto.price_calls == 0


class _IdAsSymbolCrypto:
    """CoinGecko-like client: PriceQuote.symbol is the uppercased coin id."""

    def __init__(self, prices: dict[str, Decimal]) -> None:
        self.price_calls = 0
        self.last_price_ids: list[str] = []
        self._prices = prices

    def search(self, q: str):
        return []

    def list_all(self, *, limit: int = 250):
        return []

    def get_simple_prices(self, ids, vs: str = "usd"):
        self.price_calls += 1
        self.last_price_ids = [str(i) for i in ids]
        now = datetime.now(timezone.utc)
        out: list[PriceQuote] = []
        for coin_id in ids:
            key = str(coin_id).lower()
            if key not in self._prices:
                continue
            out.append(
                PriceQuote(
                    asset_type="crypto",
                    symbol=key.upper(),
                    price=self._prices[key],
                    currency="USD",
                    as_of=now,
                )
            )
        return out

    def get_market_chart(self, id: str, range: str) -> list:
        return []


def test_get_quotes_matches_coingecko_id_as_symbol() -> None:
    """HTTP client returns symbol=BITCOIN; match by requested asset_id."""
    crypto = _IdAsSymbolCrypto({"bitcoin": Decimal("65000")})
    svc, _, _, cache = _svc(crypto=crypto)

    quotes = svc.get_quotes([("crypto", "BTC", "bitcoin")])

    assert len(quotes) == 1
    assert quotes[0].symbol == "BTC"
    assert quotes[0].price == Decimal("65000")
    assert crypto.last_price_ids == ["bitcoin"]
    assert cache.put_calls == 1


def test_get_quotes_does_not_assign_unrelated_single_quote() -> None:
    """One leftover quote must not be bound to a different requested id."""
    crypto = _IdAsSymbolCrypto({"ethereum": Decimal("3500")})
    svc, _, _, cache = _svc(crypto=crypto)

    quotes = svc.get_quotes([("crypto", "BTC", "bitcoin")])

    assert quotes == []
    assert cache.put_calls == 0


def test_get_quotes_batch_does_not_cross_assign_id_symbols() -> None:
    crypto = _IdAsSymbolCrypto({"bitcoin": Decimal("65000")})
    svc, _, _, cache = _svc(crypto=crypto)

    quotes = svc.get_quotes(
        [
            ("crypto", "BTC", "bitcoin"),
            ("crypto", "ETH", "ethereum"),
        ]
    )

    assert len(quotes) == 1
    assert quotes[0].symbol == "BTC"
    assert quotes[0].price == Decimal("65000")
    cached_eth = cache.get("crypto", "ETH", allow_expired=True)
    assert cached_eth is None


def test_get_quotes_missing_asset_id_does_not_cache_other_coin() -> None:
    """Fallback request is symbol.lower(); do not store a different coin as BTC."""
    crypto = _IdAsSymbolCrypto({"bitcoin": Decimal("65000")})
    svc, _, _, cache = _svc(crypto=crypto)

    quotes = svc.get_quotes([("crypto", "BTC")])

    assert quotes == []
    assert crypto.last_price_ids == ["btc"]
    assert cache.get("crypto", "BTC", allow_expired=True) is None


def test_http_vnstock_search_tries_live_then_fixture(monkeypatch) -> None:
    from app.adapters.vnstock.http_client import HttpVnstockClient
    from app.ports.market import AssetSearchResult

    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    live_hit = AssetSearchResult(
        symbol="AAA",
        name="Live Co",
        asset_id="AAA",
        asset_type="stock",
        currency="VND",
    )
    monkeypatch.setattr(client, "_live_search", lambda q: [live_hit])
    results = client.search("aaa")
    assert results[0].symbol == "AAA"
    assert results[0].name == "Live Co"


def test_http_vnstock_search_falls_back_when_live_empty(monkeypatch) -> None:
    from app.adapters.vnstock.http_client import HttpVnstockClient

    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_live_search", lambda q: [])
    results = client.search("vinamilk")
    assert any(r.symbol == "VNM" for r in results)


def test_http_vnstock_history_tries_live_then_fixture(monkeypatch) -> None:
    from app.adapters.vnstock.http_client import HttpVnstockClient

    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_live_history", lambda s, r: [[1, 2.5]])
    assert client.get_history("VNM", "7d") == [[1, 2.5]]

    monkeypatch.setattr(client, "_live_history", lambda s, r: (_ for _ in ()).throw(RuntimeError("down")))
    # fixture default is empty
    assert client.get_history("VNM", "7d") == []
