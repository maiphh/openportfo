"""Chat tools mutate the authenticated user's holdings only."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.ports.users import UserProfile
from app.services.holdings_service import HoldingsService
from app.services.llm.registry import ToolContext
from app.services.llm.tools import (
    ToolError,
    add_holding,
    analyze_asset,
    build_default_registry,
    remove_holding,
)
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from app.services.watchlist_service import WatchlistService
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.watchlist import InMemoryWatchlistRepo


def _ctx(user_id: str = "alice") -> tuple[ToolContext, InMemoryHoldingsRepo]:
    holdings_repo = InMemoryHoldingsRepo()
    watch_repo = InMemoryWatchlistRepo()
    market = MarketService(
        FixtureCryptoMarketClient(),
        FixtureStockMarketClient(),
        InMemoryPriceCacheRepo(),
    )
    ctx = ToolContext(
        user=UserProfile(user_id=user_id, email=f"{user_id}@example.com"),
        holdings=HoldingsService(holdings_repo),
        watchlist=WatchlistService(watch_repo),
        portfolio=PortfolioService(holdings_repo, market),
        market=market,
    )
    return ctx, holdings_repo


def test_add_holding_from_amount_and_price() -> None:
    ctx, repo = _ctx()
    result = add_holding(
        {"symbol": "btc", "price": "50000", "amount": "10", "currency": "USD"},
        ctx,
    )
    assert result["ok"] is True
    assert result["action"] == "created"
    held = repo.list("alice")
    assert len(held) == 1
    assert held[0].symbol == "BTC"
    assert held[0].qty == Decimal("10") / Decimal("50000")
    assert held[0].avg_cost == Decimal("50000")
    assert held[0].asset_id == "bitcoin"


def test_add_holding_increases_existing_weighted() -> None:
    ctx, repo = _ctx()
    add_holding({"symbol": "BTC", "qty": "1", "price": "100", "currency": "USD"}, ctx)
    result = add_holding({"symbol": "BTC", "qty": "1", "price": "300", "currency": "USD"}, ctx)
    assert result["action"] == "increased"
    held = repo.list("alice")[0]
    assert held.qty == Decimal("2")
    assert held.avg_cost == Decimal("200")


def test_remove_holding_deletes() -> None:
    ctx, repo = _ctx()
    add_holding({"symbol": "BTC", "qty": "1", "price": "100"}, ctx)
    result = remove_holding({"symbol": "bitcoin"}, ctx)
    assert result["ok"] is True
    assert result["action"] == "deleted"
    assert repo.list("alice") == []


def test_remove_holding_rejects_non_positive_qty() -> None:
    ctx, repo = _ctx()
    add_holding({"symbol": "BTC", "qty": "1", "price": "100"}, ctx)
    with pytest.raises(ToolError, match="greater than 0"):
        remove_holding({"symbol": "BTC", "qty": "-1"}, ctx)
    assert repo.list("alice")[0].qty == Decimal("1")


def test_add_holding_rejects_mixed_currency() -> None:
    ctx, repo = _ctx()
    add_holding({"symbol": "BTC", "qty": "1", "price": "100", "currency": "USD"}, ctx)
    with pytest.raises(ToolError, match="currency"):
        add_holding({"symbol": "BTC", "qty": "1", "price": "100", "currency": "VND"}, ctx)
    assert repo.list("alice")[0].currency == "USD"


def test_remove_holding_partial_qty() -> None:
    ctx, repo = _ctx()
    add_holding({"symbol": "BTC", "qty": "2", "price": "100"}, ctx)
    result = remove_holding({"symbol": "BTC", "qty": "0.5"}, ctx)
    assert result["action"] == "reduced"
    assert repo.list("alice")[0].qty == Decimal("1.5")


def test_tools_are_user_scoped() -> None:
    alice, repo = _ctx("alice")
    bob, _ = _ctx("bob")
    bob.holdings = alice.holdings  # same repo, different user on ctx
    add_holding({"symbol": "BTC", "qty": "1", "price": "100"}, alice)
    add_holding({"symbol": "ETH", "qty": "1", "price": "10"}, bob)
    assert [h.symbol for h in repo.list("alice")] == ["BTC"]
    assert [h.symbol for h in repo.list("bob")] == ["ETH"]


def test_analyze_asset_returns_quote_data() -> None:
    ctx, _ = _ctx()
    result = analyze_asset({"query": "bitcoin"}, ctx)
    assert result["ok"] is True
    assert result["data"]["resolved"]["symbol"] == "BTC"
    assert result["data"]["quote"] is not None


def test_registry_unknown_tool() -> None:
    ctx, _ = _ctx()
    registry = build_default_registry()
    executed = registry.execute("nope", {}, ctx)
    assert executed.ok is False
    assert "Unknown tool" in executed.result["error"]


def test_registry_has_expected_tools() -> None:
    names = set(build_default_registry()._tools)
    assert {
        "add_holding",
        "remove_holding",
        "get_portfolio",
        "analyze_asset",
        "analyze_portfolio",
        "search_assets",
    } <= names
