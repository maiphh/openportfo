"""POST /api/chat and GET /api/chat/models — auth, tools, model policy."""

from __future__ import annotations

from decimal import Decimal
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.core.deps import (
    set_asset_detail_service,
    set_chat_idempotency_repo,
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
from app.ports.llm import LlmProviderError
from app.api import chat as chat_api
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
    set_chat_idempotency_repo(None)
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
    set_chat_idempotency_repo(None)
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
        json={"message": "Add btc, price 50000, amount 10 usd", "clientRequestId": "req-legacy-write"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["reply"] == "Added BTC."
    assert body["toolCalls"][0]["name"] == "add_holding"
    assert body["toolCalls"][0]["ok"] is True
    assert "arguments" not in body["toolCalls"][0]
    assert "result" not in body["toolCalls"][0]
    assert body["responseVersion"] == 2
    assert body["usage"] == {"available": False, "redacted": True}
    assert body["triedModels"] == []
    rows = holdings.list("alice")
    assert len(rows) == 1
    assert rows[0].qty == Decimal("10") / Decimal("50000")
    assert holdings.list("bob") == []


def test_chat_request_id_replays_completed_mutation_without_repeating_provider_or_write() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(
                    id="write-1",
                    name="add_holding",
                    arguments={"symbol": "BTC", "price": "50000", "amount": "10", "currency": "USD"},
                )
            ),
            completion_text("Added BTC."),
        ]
    )
    client, holdings = _make_client(provider)
    payload = {"message": "Add btc", "clientRequestId": "req-123"}
    first = client.post("/api/chat", headers=_auth("alice"), json=payload)
    second = client.post("/api/chat", headers=_auth("alice"), json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["reply"] == first.json()["reply"]
    assert len(provider.calls) == 2
    assert len(holdings.list("alice")) == 1


def test_chat_legacy_response_preserves_safe_tried_models_on_replay() -> None:
    completion = completion_text("hello")
    completion.tried_models = ["provider/route-a", "provider/route-b"]
    client, _ = _make_client(ScriptedLlmProvider([completion]))
    payload = {"message": "hello", "clientRequestId": "req-routes"}
    first = client.post("/api/chat", headers=_auth("alice"), json=payload)
    second = client.post("/api/chat", headers=_auth("alice"), json=payload)
    assert first.status_code == 200
    assert first.json()["triedModels"] == ["provider/route-a", "provider/route-b"]
    assert second.status_code == 200
    assert second.json()["triedModels"] == first.json()["triedModels"]


def test_legacy_chat_rejects_unprotected_mutation_without_executing_write() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(
                    id="write-1",
                    name="add_holding",
                    arguments={"symbol": "BTC", "price": "50000", "amount": "10", "currency": "USD"},
                )
            ),
            completion_text("Added BTC."),
        ]
    )
    client, holdings = _make_client(provider)
    response = client.post("/api/chat", headers=_auth("alice"), json={"message": "Add btc"})
    assert response.status_code == 400
    assert "clientRequestId" in response.json()["detail"]
    assert holdings.list("alice") == []


def test_stream_requires_request_id_before_opening_sse() -> None:
    client, _ = _make_client(ScriptedLlmProvider([completion_text("hello")]))
    response = client.post("/api/chat/stream", headers=_auth("alice"), json={"message": "hello"})
    assert response.status_code == 400
    assert "clientRequestId" in response.json()["detail"]


def test_chat_request_id_marks_post_mutation_provider_failure_ambiguous() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(
                    id="write-1",
                    name="add_holding",
                    arguments={"symbol": "BTC", "price": "50000", "amount": "10", "currency": "USD"},
                )
            ),
            LlmProviderError("upstream payload must stay private"),
        ]
    )
    client, holdings = _make_client(provider)
    payload = {"message": "Add btc", "clientRequestId": "req-ambiguous"}
    failed = client.post("/api/chat", headers=_auth("alice"), json=payload)
    replay = client.post("/api/chat", headers=_auth("alice"), json=payload)
    assert failed.status_code == 502
    assert "may have completed" in failed.json()["detail"]
    assert replay.status_code == 502
    assert "may have completed" in replay.json()["detail"]
    assert len(holdings.list("alice")) == 1
    assert len(provider.calls) == 2


def test_chat_stream_preflight_returns_http_errors_before_sse() -> None:
    client, _ = _make_client(None)
    unconfigured = client.post(
        "/api/chat/stream",
        headers=_auth("alice"),
        json={"message": "hello", "clientRequestId": "req-preflight"},
    )
    assert unconfigured.status_code == 503
    client, _ = _make_client(ScriptedLlmProvider([completion_text("no")]))
    invalid_model = client.post(
        "/api/chat/stream",
        headers=_auth("alice"),
        json={"message": "hello", "model": "openai/gpt-4o", "freeOnly": True, "clientRequestId": "req-model"},
    )
    assert invalid_model.status_code == 400


def test_chat_stream_emits_heartbeat_for_idle_provider(monkeypatch: Any) -> None:
    provider = ScriptedLlmProvider([completion_text("hello")])
    original_complete = provider.complete

    def slow_complete(*args: Any, **kwargs: Any) -> Any:
        time.sleep(0.04)
        return original_complete(*args, **kwargs)

    provider.complete = slow_complete  # type: ignore[method-assign]
    monkeypatch.setattr(chat_api, "_STREAM_HEARTBEAT_SECONDS", 0.01)
    client, _ = _make_client(provider)
    response = client.post(
        "/api/chat/stream",
        headers=_auth("alice"),
        json={"message": "hello", "clientRequestId": "req-heartbeat"},
    )
    assert response.status_code == 200
    assert "event: heartbeat" in response.text
    assert "event: message" in response.text


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


def test_chat_stream_exposes_only_safe_activity_metadata() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(
                ToolCall(
                    id="secret-call-id",
                    name="add_holding",
                    arguments={"symbol": "BTC", "token": "do-not-publish"},
                )
            ),
            completion_text("Added BTC."),
        ]
    )
    client, _ = _make_client(provider)
    res = client.post(
        "/api/chat/stream",
        headers=_auth("alice"),
        json={"message": "Add btc", "clientRequestId": "req-safe-stream"},
    )
    assert res.status_code == 200, res.text
    assert "event: status" in res.text
    assert '"name":"add_holding"' in res.text
    assert '"label":"Updating holdings"' in res.text
    assert "secret-call-id" not in res.text
    assert "do-not-publish" not in res.text
    assert '"arguments"' not in res.text
    assert '"result"' not in res.text
    assert '"prompt_tokens"' not in res.text
    assert '"userId"' not in res.text


def test_chat_stream_orders_failed_tool_activity_before_final_message() -> None:
    provider = ScriptedLlmProvider(
        [
            completion_tools(ToolCall(id="unknown", name="model_invented_tool", arguments={"secret": "x"})),
            completion_text("I could not use that action."),
        ]
    )
    client, _ = _make_client(provider)
    response = client.post(
        "/api/chat/stream",
        headers=_auth("alice"),
        json={"message": "do it", "clientRequestId": "req-failed-tool"},
    )
    assert response.status_code == 200
    assert response.text.index('"status":"started"') < response.text.index('"status":"failed"')
    assert response.text.index('"status":"failed"') < response.text.index('event: message')
    assert "model_invented_tool" not in response.text
    assert '"name":"assistant_action"' in response.text
