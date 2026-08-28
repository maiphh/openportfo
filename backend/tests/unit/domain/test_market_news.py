"""Unit tests for market-relevance and asset keyword matching."""

from __future__ import annotations

from app.domain.market_news import (
    classify_markets,
    is_market_relevant,
    matches_asset_query,
)


def test_classify_stock_vs_crypto() -> None:
    assert classify_markets("VN-Index climbs on bank stocks") == {"stock"}
    assert classify_markets("Thị trường chứng khoán tăng điểm") == {"stock"}
    assert classify_markets("Bitcoin ETF inflows surge") == {"crypto"}
    assert classify_markets("Crypto markets turn volatile") == {"crypto"}
    both = classify_markets("Stock market and bitcoin rally")
    assert both == {"stock", "crypto"}


def test_classify_via_symbol_tags() -> None:
    assert classify_markets("Company expands", symbols=["VNM"]) == {"stock"}
    assert classify_markets("Network upgrade", symbols=["BTC"]) == {"crypto"}


def test_asset_query_matches_symbol_or_name() -> None:
    assert matches_asset_query(
        "Vinamilk expands exports",
        symbols=["VNM"],
        queries=["VNM", "Vinamilk"],
    )
    assert matches_asset_query(
        "Bitcoin holds support",
        symbols=[],
        queries=["BTC", "Bitcoin"],
    )
    assert not matches_asset_query(
        "Oil prices steady",
        symbols=[],
        queries=["VNM", "Vinamilk"],
    )


def test_non_market_titles_rejected() -> None:
    assert not is_market_relevant("Celebrity wedding photos")
    assert not is_market_relevant("")
