"""Public market overview routes (no auth — dashboard widgets)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.deps import get_crypto_market_client, get_stock_market_client
from app.ports.market import (
    CryptoMarketClient,
    HeatmapSector,
    QuoteGroup,
    QuoteRow,
    StockMarketClient,
)

router = APIRouter(tags=["markets"])

_MARKETS_CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=120"


def _ok(body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(content=body, headers={"Cache-Control": _MARKETS_CACHE_CONTROL})


def _sector_to_dict(sector: HeatmapSector) -> dict[str, Any]:
    return {
        "name": sector.name,
        "stocks": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "changePct": s.change_pct,
                "marketCap": s.market_cap,
            }
            for s in sector.stocks
        ],
    }


def _quote_row_to_dict(row: QuoteRow) -> dict[str, Any]:
    return {
        "symbol": row.symbol,
        "name": row.name,
        "value": row.value,
        "change": row.change,
        "changePct": row.change_pct,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "prev": row.prev,
    }


def _group_to_dict(group: QuoteGroup) -> dict[str, Any]:
    return {
        "name": group.name,
        "rows": [_quote_row_to_dict(r) for r in group.rows],
    }


@router.get("/api/markets/heatmap")
def market_heatmap(
    exchange: str = Query(default="HOSE"),
    limit: int = Query(default=100, ge=1, le=300),
    stock: StockMarketClient = Depends(get_stock_market_client),
) -> JSONResponse:
    """Vietnam stock heatmap grouped by industry (vnstock-backed).

    Public endpoint for the dashboard treemap. Tile size uses market cap when
    Insights is available, otherwise session traded value from the quote board.
    """
    board = (exchange or "HOSE").strip().upper() or "HOSE"
    try:
        sectors = stock.get_heatmap(exchange=board, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Heatmap unavailable: {exc}",
        ) from exc
    return _ok({
        "exchange": board,
        "limit": limit,
        "sectors": [_sector_to_dict(s) for s in sectors],
        "source": "vnstock",
    })


@router.get("/api/markets/quotes")
def market_quotes(
    exchange: str = Query(default="HOSE"),
    limit: int = Query(default=80, ge=1, le=300),
    stock: StockMarketClient = Depends(get_stock_market_client),
) -> JSONResponse:
    """Vietnam stock quote board grouped by industry (vnstock-backed)."""
    board = (exchange or "HOSE").strip().upper() or "HOSE"
    try:
        groups = stock.get_quotes(exchange=board, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Quotes unavailable: {exc}",
        ) from exc
    return _ok({
        "exchange": board,
        "limit": limit,
        "groups": [_group_to_dict(g) for g in groups],
        "source": "vnstock",
    })


@router.get("/api/markets/crypto/heatmap")
def crypto_heatmap(
    limit: int = Query(default=100, ge=1, le=300),
    crypto: CryptoMarketClient = Depends(get_crypto_market_client),
) -> JSONResponse:
    """Crypto heatmap grouped by category (CoinGecko-backed)."""
    try:
        sectors = crypto.get_heatmap(limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Heatmap unavailable: {exc}",
        ) from exc
    return _ok({
        "limit": limit,
        "sectors": [_sector_to_dict(s) for s in sectors],
        "source": "coingecko",
    })


@router.get("/api/markets/crypto/quotes")
def crypto_quotes(
    limit: int = Query(default=80, ge=1, le=300),
    crypto: CryptoMarketClient = Depends(get_crypto_market_client),
) -> JSONResponse:
    """Crypto quote board grouped by category (CoinGecko-backed, USD)."""
    try:
        groups = crypto.get_quotes(limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Quotes unavailable: {exc}",
        ) from exc
    return _ok({
        "limit": limit,
        "groups": [_group_to_dict(g) for g in groups],
        "source": "coingecko",
    })
