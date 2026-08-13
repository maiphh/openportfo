"""Live VN listing/search uses vnstock; catalog only if the library fails."""

from __future__ import annotations

from decimal import Decimal

from app.adapters.vnstock.http_client import HttpVnstockClient
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
