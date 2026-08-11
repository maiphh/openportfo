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
