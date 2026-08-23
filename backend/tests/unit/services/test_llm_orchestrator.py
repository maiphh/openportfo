"""Orchestrator tool loop with a scripted model."""

from __future__ import annotations

from decimal import Decimal

from app.ports.llm import ToolCall
from app.ports.users import UserProfile
from app.services.holdings_service import HoldingsService
from app.services.llm.orchestrator import ChatOrchestrator, _sanitize_assistant_text
from app.services.llm.registry import ToolContext, ToolRegistry, ToolSpec
from app.services.llm.tools import build_default_registry
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService
from app.services.watchlist_service import WatchlistService
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.llm import ScriptedLlmProvider, completion_text, completion_tools
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.watchlist import InMemoryWatchlistRepo


def _ctx(repo: InMemoryHoldingsRepo) -> ToolContext:
    market = MarketService(
        FixtureCryptoMarketClient(),
        FixtureStockMarketClient(),
        InMemoryPriceCacheRepo(),
    )
    return ToolContext(
        user=UserProfile(user_id="alice", email="alice@example.com"),
        holdings=HoldingsService(repo),
        watchlist=WatchlistService(InMemoryWatchlistRepo()),
        portfolio=PortfolioService(repo, market),
        market=market,
    )


def test_orchestrator_add_then_reply() -> None:
    repo = InMemoryHoldingsRepo()
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(
                    id="call_1",
                    name="add_holding",
                    arguments={
                        "symbol": "BTC",
                        "price": "50000",
                        "amount": "10",
                        "currency": "USD",
                    },
                )
            ),
            completion_text("Added 0.0002 BTC at 50000 USD."),
        ]
    )
    orch = ChatOrchestrator(provider, build_default_registry(), max_rounds=4)
    result = orch.run("Add btc, price 50000, amount 10 usd", _ctx(repo))
    assert "0.0002" in result.reply or "BTC" in result.reply
    assert result.tool_calls[0].ok is True
    assert result.tool_calls[0].name == "add_holding"
    held = repo.list("alice")
    assert len(held) == 1
    assert held[0].qty == Decimal("10") / Decimal("50000")
    # second provider call received a tool result message
    roles = [m.role for m in provider.calls[1]["messages"]]
    assert "tool" in roles


def test_orchestrator_plain_reply_no_tools() -> None:
    repo = InMemoryHoldingsRepo()
    provider = ScriptedLlmProvider([completion_text("Hello, I can help with your book.")])
    orch = ChatOrchestrator(provider, build_default_registry())
    result = orch.run("hi", _ctx(repo))
    assert result.tool_calls == []
    assert "help" in result.reply
    assert result.rounds == 1


def test_orchestrator_uses_request_runtime_parameters() -> None:
    provider = ScriptedLlmProvider([completion_text("runtime")])
    result = ChatOrchestrator(
        provider,
        build_default_registry(),
        max_tokens=321,
        temperature=0.25,
        top_p=0.8,
    ).run("hi", _ctx(InMemoryHoldingsRepo()))
    assert result.reply == "runtime"
    assert provider.calls[0]["max_tokens"] == 321
    assert provider.calls[0]["temperature"] == 0.25
    assert provider.calls[0]["top_p"] == 0.8


def test_orchestrator_remove_after_add() -> None:
    repo = InMemoryHoldingsRepo()
    ctx = _ctx(repo)
    ctx.holdings.create_holding(
        "alice",
        asset_type="crypto",
        symbol="BTC",
        qty="1",
        avg_cost="100",
        currency="USD",
        asset_id="bitcoin",
    )
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(id="c1", name="remove_holding", arguments={"symbol": "BTC"})
            ),
            completion_text("Removed BTC."),
        ]
    )
    result = ChatOrchestrator(provider, build_default_registry()).run("remove my btc", ctx)
    assert result.tool_calls[0].ok is True
    assert repo.list("alice") == []


def test_orchestrator_drops_unmatched_hidden_reasoning_opening_tag() -> None:
    assert _sanitize_assistant_text("<think>secret internal chain\nDo not show this") == ""
    assert _sanitize_assistant_text("Visible <analysis>hidden") == "Visible"
    assert _sanitize_assistant_text("[reasoning]hidden[/reasoning] Answer") == "Answer"


def test_orchestrator_fences_mutating_tool_before_execution() -> None:
    events: list[str] = []
    registry = ToolRegistry()

    def write_handler(_args: dict, _ctx: ToolContext) -> dict:
        events.append("execute")
        return {"ok": True}

    registry.register(
        ToolSpec(
            name="write_test",
            description="test write",
            parameters={"type": "object"},
            handler=write_handler,
            public_label="Updating test data",
            mutating=True,
        )
    )
    provider = ScriptedLlmProvider(
        [
            completion_tools(ToolCall(id="write", name="write_test", arguments={})),
            completion_text("done"),
        ]
    )
    result = ChatOrchestrator(provider, registry).run(
        "write",
        _ctx(InMemoryHoldingsRepo()),
        before_mutating_tool=lambda _name: (events.append("mark") or True),
    )
    assert result.reply == "done"
    assert events == ["mark", "execute"]
