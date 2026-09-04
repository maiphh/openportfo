"""FastAPI application factory."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

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
from app.core.config import (
    Settings,
    frontend_bundle_present,
    get_settings,
    resolve_frontend_dir,
)

logger = logging.getLogger(__name__)

# First URL segments the SPA fallback must never hijack (API, health, docs).
_FALLBACK_EXCLUDED_FIRST_SEGMENTS = frozenset(
    {"api", "health", "docs", "openapi.json", "redoc"}
)

_FRONTEND_NOT_BUNDLED = {"detail": "frontend not bundled"}


def _is_excluded_path(full_path: str) -> bool:
    """True when a fallback path belongs to API/health/docs, not the SPA."""
    first = (full_path or "").split("/", 1)[0].strip().lower()
    return first in _FALLBACK_EXCLUDED_FIRST_SEGMENTS


def _safe_join(root: Path, full_path: str) -> Path | None:
    """Join an untrusted URL path under root, rejecting path traversal."""
    candidate = (root / (full_path or "").strip("/")).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _resolve_bundle_dir(settings: Settings) -> Path | None:
    """Return the bundle dir to serve, or None for API-only mode.

    API-only when ``SERVE_FRONTEND=false`` or when the resolved dir has no
    ``index.html`` (missing/empty dir warns instead of failing startup).
    """
    if not settings.serve_frontend:
        return None
    resolved = resolve_frontend_dir(settings.frontend_dir)
    if not frontend_bundle_present(settings.frontend_dir):
        logger.warning(
            "frontend not bundled (SERVE_FRONTEND=true but %s has no "
            "index.html); running API-only",
            resolved,
        )
        return None
    return resolved


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    """Serve the prebuilt Next.js export after all ``/api/*`` routers (D4).

    The SPA fallback overrides ``router.default`` (the no-match handler)
    instead of registering a ``/{full_path:path}`` route, so every
    registered route — including ones added after ``create_app()`` — keeps
    precedence and only truly-unmatched GETs reach the fallback:

    - ``/_next/*`` static assets via ``StaticFiles`` (correct MIME);
    - ``GET /`` serves ``index.html`` (or JSON 404 when API-only);
    - other unmatched non-API GETs serve exact files, trailing-slash
      ``index.html`` dirs, else the SPA ``index.html`` fallback;
    - ``/api/*``, ``/health``, ``/docs``, ``/openapi.json``, ``/redoc``
      never return HTML (JSON 404 when unmatched).
    """
    frontend_dir = _resolve_bundle_dir(settings)

    if frontend_dir is not None:
        next_dir = frontend_dir / "_next"
        if next_dir.is_dir():
            app.mount(
                "/_next",
                StaticFiles(directory=next_dir),
                name="frontend-next",
            )

    original_default = app.router.default

    async def _spa_default(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("method") != "GET":
            await original_default(scope, receive, send)
            return
        stripped = (scope.get("path") or "/").strip("/")
        if _is_excluded_path(stripped):
            await JSONResponse(status_code=404, content={"detail": "Not Found"})(
                scope, receive, send
            )
            return
        if frontend_dir is None:
            await JSONResponse(
                status_code=404, content=dict(_FRONTEND_NOT_BUNDLED)
            )(scope, receive, send)
            return
        if not stripped:
            await FileResponse(
                frontend_dir / "index.html", media_type="text/html; charset=utf-8"
            )(scope, receive, send)
            return
        candidate = _safe_join(frontend_dir, stripped)
        if candidate is not None:
            if candidate.is_file():
                await FileResponse(candidate)(scope, receive, send)
                return
            if candidate.is_dir():
                index = candidate / "index.html"
                if index.is_file():
                    await FileResponse(index, media_type="text/html; charset=utf-8")(
                        scope, receive, send
                    )
                    return
        await FileResponse(
            frontend_dir / "index.html", media_type="text/html; charset=utf-8"
        )(scope, receive, send)

    app.router.default = _spa_default  # type: ignore[method-assign]


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
    # Static UI fallback last so /api/*, /health, /docs, /openapi.json keep
    # precedence over the SPA fallback (BL-031, single-EB hosting).
    _mount_frontend(app, settings)
    return app


app = create_app()
