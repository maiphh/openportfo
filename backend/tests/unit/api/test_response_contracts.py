"""OpenAPI and response-boundary tests for news and history contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.deps import (
    set_crypto_market_client,
    set_history_service,
    set_object_storage,
    set_stock_market_client,
    set_user_profile_repo,
)
from app.main import create_app
from app.services.history_service import HistoryService, build_history_key
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.storage import InMemoryObjectStorage
from tests.fakes.users import InMemoryUserProfileRepo


def _auth(uid: str = "u1") -> dict[str, str]:
    return {"Authorization": f"Bearer fake:{uid}"}


def _openapi_schema(document: dict, name: str) -> dict:
    return document["components"]["schemas"][name]


def test_openapi_documents_privacy_and_history_cache_contracts() -> None:
    document = create_app().openapi()
    schemas = document["components"]["schemas"]

    news_response = document["paths"]["/api/news"]["get"]["responses"]["200"]
    assert news_response["content"]["application/json"]["schema"]["items"] == {
        "$ref": "#/components/schemas/NewsItemResponse"
    }
    news = _openapi_schema(document, "NewsItemResponse")
    assert "keywords" not in news["properties"]
    assert "publishedAt" in news["properties"]
    assert "url" not in news["required"]

    history_response = document["paths"]["/api/assets/{asset_id}/history"]["get"]["responses"]["200"]
    assert history_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HistoryResponse"
    }
    history = _openapi_schema(document, "HistoryResponse")
    assert {"source", "stale", "cachedAt", "expiresAt"} <= set(history["properties"])
    assert "cachedAt" not in history["required"]
    assert "expiresAt" not in history["required"]

    detail_history_response = document["paths"]["/api/assets/{asset_type}/{slug}/history"]["get"]["responses"]["200"]
    assert detail_history_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AssetHistoryResponse"
    }
    assert "AssetHistoryResponse" in schemas


def test_stale_history_response_keeps_last_good_points_and_optional_metadata() -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    storage = InMemoryObjectStorage()
    storage.seed(
        build_history_key("crypto", "bitcoin", "7d"),
        {
            "assetId": "bitcoin",
            "range": "7d",
            "type": "crypto",
            "points": [{"t": "2026-08-19T00:00:00+00:00", "price": Decimal("64000")}],
            "cachedAt": "2026-08-19T00:00:00+00:00",
            "expiresAt": "2026-08-19T01:00:00+00:00",
        },
    )
    crypto = FixtureCryptoMarketClient()
    stock = FixtureStockMarketClient()
    service = HistoryService(storage, crypto, stock, clock=lambda: now)

    set_user_profile_repo(InMemoryUserProfileRepo())
    set_object_storage(storage)
    set_crypto_market_client(crypto)
    set_stock_market_client(stock)
    set_history_service(service)
    try:
        response = TestClient(create_app()).get(
            "/api/assets/bitcoin/history",
            params={"range": "7d", "type": "crypto"},
            headers=_auth(),
        )
    finally:
        set_user_profile_repo(None)
        set_object_storage(None)
        set_crypto_market_client(None)
        set_stock_market_client(None)
        set_history_service(None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "cache"
    assert body["stale"] is True
    assert body["cachedAt"] == "2026-08-19T00:00:00+00:00"
    assert body["expiresAt"] == "2026-08-19T01:00:00+00:00"
    assert body["points"] == [
        {"t": "2026-08-19T00:00:00+00:00", "price": "64000", "priceDisplay": None}
    ]
