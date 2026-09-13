"""One-shot live demo (prints replies). Not collected by pytest (underscore)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running as a script from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("OPENPORTFO_DISABLE_ENV_FILE", "0")

from app.core.config import clear_settings_cache  # noqa: E402
from app.core.deps import (  # noqa: E402
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
from app.main import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from tests.fakes.holdings import InMemoryHoldingsRepo  # noqa: E402
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient  # noqa: E402
from tests.fakes.news import InMemoryNewsRepo  # noqa: E402
from tests.fakes.price_cache import InMemoryPriceCacheRepo  # noqa: E402
from tests.fakes.users import InMemoryUserProfileRepo  # noqa: E402
from tests.fakes.watchlist import InMemoryWatchlistRepo  # noqa: E402


def _key() -> str:
    path = Path(__file__).resolve().parents[2] / ".env"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("OPENROUTER_API_KEY", "")


def main() -> int:
    key = _key()
    if not key:
        print("NO_KEY")
        return 2
    os.environ["OPENROUTER_API_KEY"] = key
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_FREE_ONLY"] = "true"
    os.environ["LLM_DEFAULT_MODEL"] = "openrouter/free"
    os.environ["LLM_RETRY_MAX"] = "1"
    os.environ["LLM_RETRY_MAX_SLEEP"] = "3"
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
    auth = {"Authorization": "Bearer fake:demo-user"}

    models = client.get("/api/chat/models?free=true&tools=true", headers=auth)
    print("MODELS_STATUS", models.status_code, "count", len(models.json().get("models") or []))
    model_id = (models.json().get("defaultModel") or "openrouter/free")

    prompts = [
        "Add btc, price 50000, amount 10 usd",
        "Analyze bitcoin",
        "Analyze my portfolio",
        "Remove my BTC",
    ]
    history: list[dict[str, str]] = []
    for index, prompt in enumerate(prompts, start=1):
        print("\n=== USER ===", prompt)
        res = client.post(
            "/api/chat",
            headers=auth,
            json={
                "message": prompt,
                "model": model_id,
                "freeOnly": True,
                "history": history[-8:],
                "clientRequestId": f"live-demo-{index}",
            },
        )
        print("HTTP", res.status_code)
        if res.status_code != 200:
            print("BODY", res.text[:1500])
            continue
        body = res.json()
        print("MODEL", body.get("model"), "ROUNDS", body.get("rounds"), "TRIED", body.get("triedModels"))
        for tc in body.get("toolCalls") or []:
            ok = tc.get("ok")
            print("TOOL", tc.get("name"), "ok=" + str(ok), json.dumps(tc.get("arguments"), default=str)[:200])
        print("REPLY", (body.get("reply") or "")[:1200])
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": body.get("reply") or ""})
        print("HOLDINGS", [(h.symbol, str(h.qty), str(h.avg_cost)) for h in holdings.list("demo-user")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
