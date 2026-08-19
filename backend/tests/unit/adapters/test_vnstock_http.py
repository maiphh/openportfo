"""Live VN listing/search uses vnstock; catalog only if the library fails."""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.adapters.vnstock.catalog import fixture_heatmap_rows, stock_prices
from app.adapters.vnstock.client import FixtureVnstockClient
from app.adapters.vnstock import http_client as vnstock_http
from app.adapters.vnstock.http_client import HttpVnstockClient, _industry_label
from app.ports.market import AssetSearchResult, MarketDataError


class _FakeQuoteDF:
    columns = ("time", "close")

    def __init__(self, close: float) -> None:
        self._close = close

    def __len__(self) -> int:
        return 1

    @property
    def iloc(self):
        row = {"close": self._close, "time": "2026-08-13"}

        class _ILoc:
            def __getitem__(self, _idx):
                return row

        return _ILoc()

    def iterrows(self):
        yield 0, {"time": "2026-08-13", "close": self._close}


def _live_rows() -> list[dict]:
    return [
        {"symbol": "VNM", "organ_name": "Vinamilk"},
        {"symbol": "PNJ", "organ_name": "Phu Nhuan Jewelry Joint Stock Company"},
        {"symbol": "FPT", "organ_name": "FPT Corporation"},
    ]


def test_http_search_finds_pnj_from_live_listing(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_listing_frame", _live_rows)
    hits = client.search("PNJ")
    assert len(hits) == 1
    assert hits[0].symbol == "PNJ"
    assert "Jewelry" in hits[0].name


def test_http_list_all_uses_live_not_three_item_catalog(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_listing_frame", _live_rows)
    listed = client.list_all(limit=10)
    symbols = {r.symbol for r in listed}
    assert symbols == {"FPT", "PNJ", "VNM"}


def test_http_listing_failure_falls_back_to_catalog(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_listing_frame", lambda: None)
    hits = client.search("PNJ")
    assert any(h.symbol == "PNJ" for h in hits)


def test_http_heatmap_falls_back_to_fixture_when_live_empty(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_live_heatmap", lambda *_a, **_k: [])
    sectors = client.get_heatmap(limit=15)
    assert sectors
    assert sum(len(s.stocks) for s in sectors) <= 15


def test_industry_label_reads_icb_name() -> None:
    assert _industry_label({"icb_name3": "Banks", "industry_name": "x"}) == "Banks"
    assert _industry_label({"icb_name": "Ngân hàng"}) == "Ngân hàng"
    assert _industry_label({"industry_name": "Retail"}) == "Retail"
    assert _industry_label({"industry": "Energy"}) == "Energy"


def test_batch_quote_rows_reads_kbs_close_price(monkeypatch) -> None:
    class FakeMarket:
        def quote(self, symbol=None):
            return [
                {
                    "symbol": "VNM",
                    "close_price": 61600,
                    "reference_price": 61000,
                    "open_price": 61100,
                    "high_price": 62000,
                    "low_price": 60800,
                    "percent_change": 0.98,
                    "price_change": 600,
                    "total_value": 1e11,
                }
            ]

    mod = sys.modules.get("vnstock")
    if mod is None:
        mod = types.ModuleType("vnstock")
        monkeypatch.setitem(sys.modules, "vnstock", mod)
    monkeypatch.setattr(mod, "Market", FakeMarket, raising=False)

    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True
    rows = client._batch_quote_rows(["VNM"])
    assert rows["VNM"]["value"] == 61600
    assert rows["VNM"]["prev"] == 61000
    assert rows["VNM"]["open"] == 61100
    assert rows["VNM"]["high"] == 62000
    assert rows["VNM"]["low"] == 60800
    assert rows["VNM"]["change"] == 600
    assert rows["VNM"]["change_pct"] == pytest.approx(0.98)


def test_http_quotes_falls_back_to_fixture_when_live_empty(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    monkeypatch.setattr(client, "_live_quotes", lambda *_a, **_k: [])
    groups = client.get_quotes(limit=15)
    assert groups
    assert sum(len(g.rows) for g in groups) <= 15


def test_http_heatmap_no_fallback_raises_when_live_empty(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True
    monkeypatch.setattr(client, "_live_heatmap", lambda *_a, **_k: [])
    with pytest.raises(MarketDataError, match="heatmap unavailable"):
        client.get_heatmap(limit=15)


def test_http_quotes_no_fallback_raises_when_live_empty(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True
    monkeypatch.setattr(client, "_live_quotes", lambda *_a, **_k: [])
    with pytest.raises(MarketDataError, match="quotes unavailable"):
        client.get_quotes(limit=15)


def test_http_heatmap_no_fallback_raises_when_live_errors(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True

    def _boom(*_a, **_k):
        raise RuntimeError("vnstock down")

    monkeypatch.setattr(client, "_live_heatmap", _boom)
    with pytest.raises(MarketDataError, match="heatmap failed"):
        client.get_heatmap(limit=15)


def test_http_default_has_no_fixture_fallback() -> None:
    client = HttpVnstockClient()
    assert client._fallback is None


def test_fixture_quotes_groups_by_industry_and_respects_limit() -> None:
    client = FixtureVnstockClient()
    groups = client.get_quotes(exchange="HOSE", limit=12)
    assert groups
    total = sum(len(g.rows) for g in groups)
    assert 1 <= total <= 12
    prices = stock_prices()
    heatmap = {row[0]: row for row in fixture_heatmap_rows()}
    first = groups[0].rows[0]
    assert first.symbol in prices
    expected_value = float(prices[first.symbol][0])
    assert first.value == expected_value
    expected_pct = heatmap[first.symbol][3]
    assert first.change_pct == expected_pct
    assert first.change == pytest.approx(expected_value * expected_pct / 100.0)
    names = {g.name for g in client.get_quotes(limit=80)}
    assert "Ngân hàng" in names
    assert len(names) > 1


def test_http_search_uses_vnstock_catalog_not_fixture(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=True)
    client._live = True
    live_hit = AssetSearchResult(
        symbol="AAA",
        name="Live Co",
        asset_id="AAA",
        asset_type="stock",
        currency="VND",
    )
    monkeypatch.setattr(client, "_live_catalog", lambda: [live_hit])
    hits = client.search("aaa")
    assert hits[0].symbol == "AAA"
    assert hits[0].name == "Live Co"


def test_live_price_scaled_from_thousands_of_vnd(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True
    monkeypatch.setattr(client, "_quote_history", lambda *_a, **_k: _FakeQuoteDF(61.6))
    quotes = client.get_prices(["VNM"])
    assert len(quotes) == 1
    assert quotes[0].price == Decimal("61600")
    assert quotes[0].currency == "VND"


def test_live_history_scaled_from_thousands_of_vnd(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._live = True
    monkeypatch.setattr(client, "_quote_history", lambda *_a, **_k: _FakeQuoteDF(61.6))
    points = client.get_history("VNM", "7d")
    assert len(points) == 1
    assert points[0][1] == Decimal("61600")


_QUOTE_BOARD_ROWS = {
    "VNM": {
        "value": 61600,
        "change": 600,
        "change_pct": 0.98,
        "open": 61100,
        "high": 62000,
        "low": 60800,
        "prev": 61000,
        "size": 1e11,
    },
    "VCB": {
        "value": 91000,
        "change": 500,
        "change_pct": 0.55,
        "open": 90500,
        "high": 91500,
        "low": 90200,
        "prev": 90500,
        "size": 2e11,
    },
}


def _wire_shared_quote_board(client: HttpVnstockClient, monkeypatch, calls: dict[str, int]) -> None:
    client._live = True
    monkeypatch.setattr(client, "_insights_heatmap", lambda *_a, **_k: [])
    monkeypatch.setattr(client, "_industry_map", lambda: {"VNM": "Thực phẩm", "VCB": "Ngân hàng"})
    monkeypatch.setattr(client, "_exchange_symbols", lambda *_a, **_k: {"VNM", "VCB"})
    monkeypatch.setattr(client, "_symbol_name_map", lambda: {"VNM": "Vinamilk", "VCB": "Vietcombank"})

    def _batch(symbols):
        calls["batch"] += 1
        return {sym: dict(_QUOTE_BOARD_ROWS[sym]) for sym in symbols if sym in _QUOTE_BOARD_ROWS}

    monkeypatch.setattr(client, "_batch_quote_rows", _batch)


def test_heatmap_then_quotes_shares_quote_board_batch(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    calls = {"batch": 0}
    _wire_shared_quote_board(client, monkeypatch, calls)

    sectors = client.get_heatmap(exchange="HOSE", limit=10)
    groups = client.get_quotes(exchange="HOSE", limit=8)

    assert calls["batch"] == 1
    assert sum(len(s.stocks) for s in sectors) == 2
    assert sum(len(g.rows) for g in groups) == 2


def test_quotes_then_heatmap_shares_quote_board_batch(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    calls = {"batch": 0}
    _wire_shared_quote_board(client, monkeypatch, calls)

    client.get_quotes(exchange="HOSE", limit=8)
    client.get_heatmap(exchange="HOSE", limit=10)

    assert calls["batch"] == 1


def test_quote_board_cache_expires_after_ttl(monkeypatch) -> None:
    client = HttpVnstockClient(use_fixture_fallback=False)
    calls = {"batch": 0}
    _wire_shared_quote_board(client, monkeypatch, calls)
    clock = {"now": datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(vnstock_http, "_utc_now", lambda: clock["now"])

    client.get_heatmap(exchange="HOSE", limit=10)
    client.get_quotes(exchange="HOSE", limit=8)
    assert calls["batch"] == 1

    clock["now"] = clock["now"] + timedelta(seconds=121)
    client.get_quotes(exchange="HOSE", limit=8)
    assert calls["batch"] == 2


def test_industry_map_cached_within_ttl(monkeypatch) -> None:
    calls: list[int] = []

    class FakeListing:
        def symbols_by_industries(self):
            calls.append(1)
            return [{"symbol": "VNM", "icb_name3": "Food"}]

    mod = sys.modules.get("vnstock")
    if mod is None:
        mod = types.ModuleType("vnstock")
        monkeypatch.setitem(sys.modules, "vnstock", mod)
    monkeypatch.setattr(mod, "Listing", FakeListing, raising=False)

    client = HttpVnstockClient(use_fixture_fallback=False)
    first = client._industry_map()
    second = client._industry_map()
    assert first == {"VNM": "Food"}
    assert second is first
    assert len(calls) == 1


def test_industry_map_cache_expires_after_ttl(monkeypatch) -> None:
    calls: list[int] = []

    class FakeListing:
        def symbols_by_industries(self):
            calls.append(1)
            return [{"symbol": "VNM", "icb_name3": "Food"}]

    mod = sys.modules.get("vnstock")
    if mod is None:
        mod = types.ModuleType("vnstock")
        monkeypatch.setitem(sys.modules, "vnstock", mod)
    monkeypatch.setattr(mod, "Listing", FakeListing, raising=False)

    clock = {"now": datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(vnstock_http, "_utc_now", lambda: clock["now"])
    client = HttpVnstockClient(use_fixture_fallback=False)
    client._industry_map()
    clock["now"] = clock["now"] + timedelta(seconds=121)
    client._industry_map()
    assert len(calls) == 2
