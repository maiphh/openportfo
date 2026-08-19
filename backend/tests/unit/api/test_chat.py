"""POST /api/chat and GET /api/chat/models — auth, tools, model policy."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.core.deps import (
    set_asset_detail_service,
    set_crypto_market_client,
    set_holdings_repo,
    set_llm_provider,
    set_market_service,
    set_portfolio_service,
    set_price_cache_repo,
    set_stock_market_client,
    set_user_profile_repo,
    set_watchlist_repo,
)
from app.main import create_app
from app.ports.llm import LlmModelInfo, ToolCall
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.llm import ScriptedLlmProvider, completion_text, completion_tools
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.users import InMemoryUserProfileRepo
from tests.fakes.watchlist import InMemoryWatchlistRepo


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


def _make_client(
    provider: ScriptedLlmProvider | None,
) -> tuple[TestClient, InMemoryHoldingsRepo]:
    holdings = InMemoryHoldingsRepo()
    set_holdings_repo(holdings)
    set_watchlist_repo(InMemoryWatchlistRepo())
    set_user_profile_repo(InMemoryUserProfileRepo())
    set_crypto_market_client(FixtureCryptoMarketClient())
    set_stock_market_client(FixtureStockMarketClient())
    set_price_cache_repo(InMemoryPriceCacheRepo())
    set_market_service(None)
    set_portfolio_service(None)
    set_asset_detail_service(None)
    set_llm_provider(provider)
    return TestClient(create_app()), holdings


@pytest.fixture(autouse=True)
def _reset() -> Any:
    set_llm_provider(None)
    set_holdings_repo(None)
    set_watchlist_repo(None)
    set_user_profile_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_market_service(None)
    set_portfolio_service(None)
    set_asset_detail_service(None)
    clear_settings_cache()
    yield
    set_llm_provider(None)
    set_holdings_repo(None)
    set_watchlist_repo(None)
    set_user_profile_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_market_service(None)
    set_portfolio_service(None)
    set_asset_detail_service(None)
    clear_settings_cache()


def test_chat_requires_auth() -> None:
    client, _ = _make_client(ScriptedLlmProvider([completion_text("hi")]))
    res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_chat_unconfigured_is_503() -> None:
    client, _ = _make_client(None)
    res = client.post("/api/chat", headers=_auth("alice"), json={"message": "hello"})
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


def test_chat_rejects_empty_message() -> None:
    client, _ = _make_client(ScriptedLlmProvider([completion_text("x")]))
    res = client.post("/api/chat", headers=_auth("alice"), json={"message": "   "})
    assert res.status_code == 400


def test_chat_allows_catalog_free_model_without_suffix() -> None:
    provider = ScriptedLlmProvider(
        [completion_text("hello")],
        models=[LlmModelInfo(id="google/gemma-3", name="Gemma", free=True, tools=True)],
    )
    client, _ = _make_client(provider)
    res = client.post(
        "/api/chat",
        headers=_auth("alice"),
        json={"message": "hi", "model": "google/gemma-3", "freeOnly": True},
    )
    assert res.status_code == 200, res.text


def test_chat_rejects_paid_model_when_free_only() -> None:
    client, _ = _make_client(ScriptedLlmProvider([completion_text("x")]))
    res = client.post(
        "/api/chat",
        headers=_auth("alice"),
        json={"message": "hi", "model": "openai/gpt-4o", "freeOnly": True},
    )
    assert res.status_code == 400
    assert "free" in res.json()["detail"].lower()


def test_chat_server_free_only_ignores_client_false() -> None:
    client, _ = _make_client(ScriptedLlmProvider([completion_text("x")]))
    res = client.post(
        "/api/chat",
        headers=_auth("alice"),
        json={"message": "hi", "model": "openai/gpt-4o", "freeOnly": False},
    )
    assert res.status_code == 400
    assert "free" in res.json()["detail"].lower()


def test_chat_add_holding_via_tools() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(
                    id="1",
                    name="add_holding",
                    arguments={
                        "symbol": "BTC",
                        "price": "50000",
                        "amount": "10",
                        "currency": "USD",
                    },
                )
            ),
            completion_text("Added BTC."),
        ]
    )
    client, holdings = _make_client(provider)
    res = client.post(
        "/api/chat",
        headers=_auth("alice"),
        json={"message": "Add btc, price 50000, amount 10 usd"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["reply"] == "Added BTC."
    assert body["toolCalls"][0]["name"] == "add_holding"
    assert body["toolCalls"][0]["ok"] is True
    rows = holdings.list("alice")
    assert len(rows) == 1
    assert rows[0].qty == Decimal("10") / Decimal("50000")
    assert holdings.list("bob") == []


def test_chat_analyze_portfolio_tool() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(ToolCall(id="1", name="analyze_portfolio", arguments={})),
            completion_text("Specialist: empty book."),
            completion_text("Your book is empty."),
        ]
    )
    client, _ = _make_client(provider)
    res = client.post(
        "/api/chat",
        headers=_auth("alice"),
        json={"message": "analyze my portfo"},
    )
    assert res.status_code == 200
    assert res.json()["toolCalls"][0]["name"] == "analyze_portfolio"
    assert res.json()["toolCalls"][0]["ok"] is True


def test_list_models_requires_auth() -> None:
    client, _ = _make_client(ScriptedLlmProvider())
    assert client.get("/api/chat/models").status_code == 401


def test_list_models_from_provider() -> None:
    provider = ScriptedLlmProvider(
        models=[
            LlmModelInfo(id="foo:free", name="Foo", free=True, tools=True),
            LlmModelInfo(id="bar", name="Bar", free=False, tools=True),
        ]
    )
    client, _ = _make_client(provider)
    res = client.get("/api/chat/models?free=true", headers=_auth("alice"))
    assert res.status_code == 200
    body = res.json()
    assert body["configured"] is True
    ids = [m["id"] for m in body["models"]]
    assert "foo:free" in ids
    assert "bar" not in ids
