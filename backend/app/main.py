"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.dynamodb_viewer import router as dynamodb_viewer_router
from app.api.s3_viewer import router as s3_viewer_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.fx import router as fx_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.holdings import router as holdings_router
from app.api.markets import router as markets_router
from app.api.news import router as news_router
from app.api.portfolio import router as portfolio_router
from app.api.snapshots import router as snapshots_router
from app.api.watchlist import router as watchlist_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_api_runtime()
    env = (settings.app_env or "").strip().lower()

    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(markets_router)
    app.include_router(auth_router)
    app.include_router(holdings_router)
    app.include_router(watchlist_router)
    # History (`/api/assets/{id}/history`) must register before the generic
    # `/api/assets/{type}/{slug}` detail route so legacy chart URLs still match.
    app.include_router(history_router)
    app.include_router(assets_router)
    app.include_router(portfolio_router)
    app.include_router(snapshots_router)
    app.include_router(fx_router)
    app.include_router(news_router)
    app.include_router(chat_router)
    app.include_router(admin_router)
    if env in {"local", "test"}:
        app.include_router(s3_viewer_router)
        if (settings.dynamodb_endpoint_url or "").strip():
            app.include_router(dynamodb_viewer_router)
    return app


app = create_app()
