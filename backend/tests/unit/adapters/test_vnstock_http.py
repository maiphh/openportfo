"""Live VN listing/search uses vnstock; catalog only if the library fails."""

from __future__ import annotations

import sys
import types
from decimal import Decimal

import pytest

from app.adapters.vnstock.catalog import fixture_heatmap_rows, stock_prices
from app.adapters.vnstock.client import FixtureVnstockClient
from app.adapters.vnstock.http_client import HttpVnstockClient, _industry_label
from app.ports.market import AssetSearchResult


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
