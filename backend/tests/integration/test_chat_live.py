"""Live OpenRouter calls (skipped unless RUN_LLM_TESTS=1 and a key is present)."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.core.deps import (
    set_asset_detail_service,
    set_crypto_market_client,
    set_holdings_repo,
    set_llm_provider,
    set_market_service,
    set_news_repo,
    set_portfolio_service,
    set_price_cache_repo,
    set_stock_market_client,
    set_user_profile_repo,
    set_watchlist_repo,
)
from app.main import create_app
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.news import InMemoryNewsRepo
from tests.fakes.price_cache import InMemoryPriceCacheRepo
from tests.fakes.users import InMemoryUserProfileRepo
from tests.fakes.watchlist import InMemoryWatchlistRepo

pytestmark = pytest.mark.llm


def _dotenv_key() -> str:
    env_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if env_key:
        return env_key
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _llm_enabled() -> bool:
    flag = os.environ.get("RUN_LLM_TESTS", "").strip().lower()
    return flag in {"1", "true", "yes"} and bool(_dotenv_key())


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{user_id}"}


@pytest.fixture
def live_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, InMemoryHoldingsRepo]:
    if not _llm_enabled():
        pytest.skip("Set RUN_LLM_TESTS=1 and OPENROUTER_API_KEY to run live LLM tests")
    key = _dotenv_key()
    monkeypatch.setenv("OPENROUTER_API_KEY", key)
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_FREE_ONLY", "true")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "openrouter/free")
    monkeypatch.setenv(
        "LLM_FALLBACK_MODELS",
        "openrouter/free,meta-llama/llama-3.3-70b-instruct:free,qwen/qwen3-32b:free",
    )
    monkeypatch.setenv("LLM_RETRY_MAX", "1")
    monkeypatch.setenv("LLM_RETRY_MAX_SLEEP", "3")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "90")
    clear_settings_cache()
    set_llm_provider(None)

    holdings = InMemoryHoldingsRepo()
    set_holdings_repo(holdings)
    set_watchlist_repo(InMemoryWatchlistRepo())
    set_user_profile_repo(InMemoryUserProfileRepo())
    set_crypto_market_client(FixtureCryptoMarketClient())
    set_stock_market_client(FixtureStockMarketClient())
    set_price_cache_repo(InMemoryPriceCacheRepo())
    set_news_repo(InMemoryNewsRepo())
    set_market_service(None)
    set_portfolio_service(None)
    set_asset_detail_service(None)

    client = TestClient(create_app())
    yield client, holdings

    set_llm_provider(None)
    set_holdings_repo(None)
    set_watchlist_repo(None)
    set_user_profile_repo(None)
    set_crypto_market_client(None)
    set_stock_market_client(None)
    set_price_cache_repo(None)
    set_news_repo(None)
    set_market_service(None)
    set_portfolio_service(None)
    set_asset_detail_service(None)
    clear_settings_cache()


def _pick_model(client: TestClient) -> str | None:
    res = client.get("/api/chat/models?free=true&tools=true", headers=_auth("live-user"))
    assert res.status_code == 200, res.text
    models = res.json().get("models") or []
    ids = [m["id"] for m in models]
    preferred = [
        "openrouter/free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-32b:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ]
    for mid in preferred:
        if mid in ids:
            return mid
    return ids[0] if ids else None


def test_live_list_models(live_client: tuple[TestClient, InMemoryHoldingsRepo]) -> None:
    client, _ = live_client
    res = client.get("/api/chat/models", headers=_auth("live-user"))
    assert res.status_code == 200
    body = res.json()
    assert body["configured"] is True
    assert body["provider"] == "openrouter"
    assert isinstance(body["models"], list)


def test_live_add_remove_analyze(live_client: tuple[TestClient, InMemoryHoldingsRepo]) -> None:
    client, holdings = live_client
    model = _pick_model(client)
    user = "live-alice"

    add = client.post(
        "/api/chat",
        headers=_auth(user),
        json={
            "message": "Add btc, price 50000, amount 10 usd",
            "model": model,
            "freeOnly": True,
        },
    )
    assert add.status_code == 200, add.text
    add_body = add.json()
    assert add_body["reply"]
    rows = holdings.list(user)
    tool_names = [t["name"] for t in add_body.get("toolCalls") or []]
    assert rows or "add_holding" in tool_names, add_body
    if rows:
        assert rows[0].symbol == "BTC"
        assert rows[0].qty > 0

    analyze_coin = client.post(
        "/api/chat",
        headers=_auth(user),
        json={
            "message": "Analyze bitcoin",
            "model": model,
            "freeOnly": True,
            "history": [
                {"role": "user", "content": "Add btc, price 50000, amount 10 usd"},
                {"role": "assistant", "content": add_body["reply"]},
            ],
        },
    )
    assert analyze_coin.status_code == 200, analyze_coin.text
    coin_body = analyze_coin.json()
    assert coin_body["reply"]
    blob = (coin_body["reply"] + json_tools(coin_body)).lower()
    assert "btc" in blob or "bitcoin" in blob, coin_body["reply"]

    analyze_book = client.post(
        "/api/chat",
        headers=_auth(user),
        json={
            "message": "Analyze my portfolio",
            "model": model,
            "freeOnly": True,
        },
    )
    assert analyze_book.status_code == 200, analyze_book.text
    assert analyze_book.json()["reply"]

    remove = client.post(
        "/api/chat",
        headers=_auth(user),
        json={
            "message": "Remove my BTC holding",
            "model": model,
            "freeOnly": True,
            "history": [
                {"role": "user", "content": "Add btc, price 50000, amount 10 usd"},
                {"role": "assistant", "content": add_body["reply"]},
            ],
        },
    )
    assert remove.status_code == 200, remove.text
    remaining = holdings.list(user)
    remove_tools = [t["name"] for t in remove.json().get("toolCalls") or []]
    assert remaining == [] or "remove_holding" in remove_tools, remove.json()


def json_tools(body: dict) -> str:
    return " ".join(t.get("name") or "" for t in body.get("toolCalls") or [])
