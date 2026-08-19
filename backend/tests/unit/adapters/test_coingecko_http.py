"""CoinGecko fixture + HTTP heatmap/quotes (no live network)."""

from __future__ import annotations

import httpx
import pytest

from app.adapters.coingecko.catalog import crypto_prices, fixture_crypto_heatmap_rows
from app.adapters.coingecko.client import FixtureCoinGeckoClient
from app.adapters.coingecko.http_client import HttpCoinGeckoClient
from app.ports.market import MarketDataError


def _markets_payload() -> list[dict]:
    return [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 65000,
            "price_change_24h": 1200,
            "price_change_percentage_24h": 1.88,
            "high_24h": 66000,
            "low_24h": 63000,
            "market_cap": 1.2e12,
        },
        {
            "id": "uniswap",
            "symbol": "uni",
            "name": "Uniswap",
            "current_price": 8.5,
            "price_change_24h": 0.2,
            "price_change_percentage_24h": 2.4,
            "high_24h": 8.8,
            "low_24h": 8.1,
            "market_cap": 5e9,
        },
    ]


def test_fixture_crypto_heatmap_groups_by_category_and_respects_limit() -> None:
    client = FixtureCoinGeckoClient()
    sectors = client.get_heatmap(limit=8)
    assert sectors
    total = sum(len(s.stocks) for s in sectors)
    assert 1 <= total <= 8
    names = {s.name for s in client.get_heatmap(limit=100)}
    assert "Layer 1" in names
    assert len(names) > 1
    catalog_rows = {row[1]: row for row in fixture_crypto_heatmap_rows()}
    first = sectors[0].stocks[0]
    assert first.symbol in catalog_rows
    assert first.market_cap == catalog_rows[first.symbol][5]
    assert first.change_pct == catalog_rows[first.symbol][4]


def test_fixture_crypto_quotes_groups_by_category_and_respects_limit() -> None:
    client = FixtureCoinGeckoClient()
    groups = client.get_quotes(limit=10)
    assert groups
    total = sum(len(g.rows) for g in groups)
    assert 1 <= total <= 10
    prices = crypto_prices()
    heatmap = {row[0]: row for row in fixture_crypto_heatmap_rows()}
    first = groups[0].rows[0]
    # fixture rows: (coin_id, symbol, name, category, change_pct, market_cap)
    coin_id = next(cid for cid, rec in heatmap.items() if rec[1] == first.symbol)
    expected_value = float(prices[coin_id][0])
    assert first.value == expected_value
    expected_pct = heatmap[coin_id][4]
    assert first.change_pct == expected_pct
    assert first.change == pytest.approx(expected_value * expected_pct / 100.0)
    names = {g.name for g in client.get_quotes(limit=80)}
    assert "Layer 1" in names
    assert len(names) > 1


def test_http_crypto_heatmap_uses_markets_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/coins/markets" in str(request.url)
        return httpx.Response(200, json=_markets_payload())

    client = HttpCoinGeckoClient(transport=httpx.MockTransport(handler))
    sectors = client.get_heatmap(limit=10)
    tiles = [t for s in sectors for t in s.stocks]
    symbols = {t.symbol for t in tiles}
    assert "BTC" in symbols
    btc = next(t for t in tiles if t.symbol == "BTC")
    assert btc.change_pct == pytest.approx(1.88)
    assert btc.market_cap == pytest.approx(1.2e12)
    names = {s.name for s in sectors}
    assert "Layer 1" in names
    assert "DeFi" in names


def test_http_crypto_quotes_uses_markets_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/coins/markets" in str(request.url)
        return httpx.Response(200, json=_markets_payload())

    client = HttpCoinGeckoClient(transport=httpx.MockTransport(handler))
    groups = client.get_quotes(limit=10)
    rows = [r for g in groups for r in g.rows]
    btc = next(r for r in rows if r.symbol == "BTC")
    assert btc.value == 65000
    assert btc.change == 1200
    assert btc.change_pct == pytest.approx(1.88)
    assert btc.high == 66000
    assert btc.low == 63000
    assert btc.prev == pytest.approx(63800)
    assert btc.open == pytest.approx(63800)


def test_http_crypto_heatmap_falls_back_to_fixture(monkeypatch) -> None:
    client = HttpCoinGeckoClient(use_fixture_fallback=True)
    monkeypatch.setattr(
        client,
        "_get",
        lambda *_a, **_k: (_ for _ in ()).throw(MarketDataError("down")),
    )
    sectors = client.get_heatmap(limit=6)
    assert sectors
    assert sum(len(s.stocks) for s in sectors) <= 6


def test_http_crypto_quotes_falls_back_to_fixture(monkeypatch) -> None:
    client = HttpCoinGeckoClient(use_fixture_fallback=True)
    monkeypatch.setattr(
        client,
        "_get",
        lambda *_a, **_k: (_ for _ in ()).throw(MarketDataError("down")),
    )
    groups = client.get_quotes(limit=6)
    assert groups
    assert sum(len(g.rows) for g in groups) <= 6


def test_http_crypto_heatmap_no_fallback_raises(monkeypatch) -> None:
    client = HttpCoinGeckoClient(use_fixture_fallback=False)
    monkeypatch.setattr(
        client,
        "_get",
        lambda *_a, **_k: (_ for _ in ()).throw(MarketDataError("down")),
    )
    with pytest.raises(MarketDataError):
        client.get_heatmap(limit=6)


def test_http_crypto_quotes_no_fallback_raises(monkeypatch) -> None:
    client = HttpCoinGeckoClient(use_fixture_fallback=False)
    monkeypatch.setattr(
        client,
        "_get",
        lambda *_a, **_k: (_ for _ in ()).throw(MarketDataError("down")),
    )
    with pytest.raises(MarketDataError):
        client.get_quotes(limit=6)


def test_http_crypto_default_has_no_fixture_fallback() -> None:
    client = HttpCoinGeckoClient()
    assert client._fallback is None
