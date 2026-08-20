"""Default chatbot tools. Register additional ToolSpec entries to extend."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from datetime import datetime

from app.domain.models import CurrencyTotals, PortfolioLine
from app.domain.portfolio_math import pnl_percent
from app.ports.holdings import DuplicateHoldingError, HoldingNotFoundError, HoldingRecord
from app.ports.news import NewsItem
from app.ports.market import AssetSearchResult
from app.ports.watchlist import DuplicateWatchlistError, WatchlistNotFoundError
from app.services.asset_detail_service import AssetNotFoundError
from app.services.holdings_service import ValidationError as HoldingsValidationError
from app.services.llm.qty import QtyError, compute_qty_and_avg_cost, weighted_avg_cost
from app.services.llm.registry import ToolContext, ToolRegistry, ToolSpec
from app.services.market_service import QuoteKey, quote_to_dict, search_result_to_dict
from app.services.watchlist_service import ValidationError as WatchlistValidationError

_OBJECT = "object"
_STRING = "string"
_NUMBER = "number"


class ToolError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def _arg_str(args: dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = args.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _guess_asset_type(args: dict[str, Any]) -> Optional[str]:
    raw = _arg_str(args, "assetType", "asset_type", "type")
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in {"crypto", "stock"}:
        return lowered
    raise ToolError("assetType must be 'crypto' or 'stock'")


def resolve_asset(
    ctx: ToolContext,
    query: str,
    asset_type: Optional[str] = None,
) -> AssetSearchResult:
    needle = (query or "").strip()
    if not needle:
        raise ToolError("symbol or query is required")
    types = [asset_type] if asset_type else ["crypto", "stock"]
    last_error = "Asset not found"
    for at in types:
        hits: list[AssetSearchResult] = []
        try:
            hits = list(ctx.market.search(needle, at))
        except Exception as exc:  # noqa: BLE001
            last_error = str(getattr(exc, "detail", None) or exc)
        if not hits:
            try:
                catalog = ctx.market.list_assets(at, limit=500)
            except Exception:  # noqa: BLE001
                catalog = []
            low = needle.lower()
            hits = [
                h
                for h in catalog
                if h.symbol.lower() == low
                or h.asset_id.lower() == low
                or low in (h.name or "").lower()
            ]
        if not hits:
            continue
        exact_sym = next((h for h in hits if h.symbol.lower() == needle.lower()), None)
        exact_id = next((h for h in hits if h.asset_id.lower() == needle.lower()), None)
        return exact_sym or exact_id or hits[0]
    raise ToolError(f"{last_error}: {needle}")


def _quote_for(ctx: ToolContext, hit: AssetSearchResult) -> Optional[dict[str, Any]]:
    quotes = ctx.market.get_quotes(
        [
            QuoteKey(
                asset_type=hit.asset_type,
                symbol=hit.symbol,
                asset_id=hit.asset_id,
            )
        ]
    )
    if not quotes:
        return None
    return quote_to_dict(quotes[0], asset_id=hit.asset_id)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def _dec_str(d: Optional[Decimal]) -> Optional[str]:
    if d is None:
        return None
    return format(d, "f")


def _holding_payload(record: HoldingRecord) -> dict[str, Any]:
    return {
        "assetType": record.asset_type,
        "symbol": record.symbol,
        "assetId": record.asset_id,
        "qty": _dec_str(record.qty),
        "avgCost": _dec_str(record.avg_cost),
        "currency": record.currency,
        "note": record.note,
        "createdAt": _iso(record.created_at),
        "updatedAt": _iso(record.updated_at),
    }


def _news_item_to_dict(item: NewsItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "publishedAt": _iso(item.published_at),
        "symbols": list(item.symbols or []),
        "date": item.date,
    }


def _currency_totals_to_dict(t: CurrencyTotals) -> dict[str, Any]:
    pct = pnl_percent(t.pnl, t.cost_basis)
    return {
        "marketValue": _dec_str(t.market_value),
        "costBasis": _dec_str(t.cost_basis),
        "pnl": _dec_str(t.pnl),
        "pnlPercent": _dec_str(pct),
    }


def _line_to_dict(line: PortfolioLine) -> dict[str, Any]:
    return {
        "assetType": line.asset_type,
        "symbol": line.symbol,
        "assetId": line.asset_id,
        "qty": _dec_str(line.qty),
        "avgCost": _dec_str(line.avg_cost),
        "currency": line.currency,
        "price": _dec_str(line.price),
        "marketValue": _dec_str(line.market_value),
        "costBasis": _dec_str(line.cost_basis),
        "pnl": _dec_str(line.pnl),
        "pnlPercent": _dec_str(line.pnl_percent),
        "missingPrice": line.missing_price,
        "stale": line.stale,
        "allocation": _dec_str(line.allocation),
    }


def _portfolio_payload(view: Any) -> dict[str, Any]:
    summary = view.summary
    totals_display = None
    if summary.market_value_display is not None:
        totals_display = {
            "currency": summary.display_currency,
            "marketValue": _dec_str(summary.market_value_display),
            "costBasis": _dec_str(summary.cost_basis_display),
            "pnl": _dec_str(summary.pnl_display),
            "pnlPercent": _dec_str(summary.pnl_percent_display),
        }
    return {
        "lines": [_line_to_dict(ln) for ln in summary.lines],
        "totalsByCurrency": {
            cur: _currency_totals_to_dict(tot)
            for cur, tot in summary.totals_by_currency.items()
        },
        "totalsByAssetClass": {
            asset_type: {
                "currency": tot.currency,
                **_currency_totals_to_dict(tot),
            }
            for asset_type, tot in (summary.totals_by_asset_class or {}).items()
        },
        "totalsDisplay": totals_display,
        "displayCurrency": summary.display_currency,
        "asOf": _iso(view.as_of),
    }


def search_assets(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    q = _arg_str(args, "q", "query", "symbol") or ""
    asset_type = _guess_asset_type(args)
    types = [asset_type] if asset_type else ["crypto", "stock"]
    results: list[dict[str, Any]] = []
    last_error: Optional[str] = None
    for at in types:
        try:
            hits = ctx.market.search(q, at)
        except Exception as exc:  # noqa: BLE001
            last_error = str(getattr(exc, "detail", None) or exc)
            continue
        results.extend(search_result_to_dict(h) for h in hits[:8])
    if not results and last_error:
        return {"ok": False, "error": last_error}
    return {"ok": True, "results": results[:12]}


def add_holding(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    query = _arg_str(args, "symbol", "query", "assetId", "asset_id")
    if not query:
        raise ToolError("symbol is required")
    asset_type = _guess_asset_type(args)
    hit = resolve_asset(ctx, query, asset_type)
    currency = (_arg_str(args, "currency") or ("USD" if hit.asset_type == "crypto" else "VND")).upper()
    quote = None
    market_price: Optional[Decimal] = None
    try:
        quote = _quote_for(ctx, hit)
        if quote and quote.get("price") is not None:
            market_price = Decimal(str(quote["price"]))
    except Exception:  # noqa: BLE001
        quote = None

    try:
        qty, avg = compute_qty_and_avg_cost(
            qty=args.get("qty"),
            avg_cost=args.get("avgCost") if "avgCost" in args else args.get("avg_cost"),
            price=args.get("price"),
            amount=args.get("amount"),
            market_price=market_price,
        )
    except QtyError as exc:
        raise ToolError(exc.detail) from exc

    note = _arg_str(args, "note")
    user_id = ctx.user.user_id
    existing = None
    try:
        existing = ctx.holdings.get_holding(user_id, hit.asset_type, hit.symbol)
    except HoldingNotFoundError:
        existing = None
    except HoldingsValidationError as exc:
        raise ToolError(exc.detail) from exc

    if existing is not None and existing.currency.upper() != currency:
        raise ToolError(
            f"Holding {hit.symbol} is already in {existing.currency}; "
            f"pass currency={existing.currency} (cannot mix cost currencies)"
        )

    try:
        if existing is None:
            created = ctx.holdings.create_holding(
                user_id,
                asset_type=hit.asset_type,
                symbol=hit.symbol,
                qty=qty,
                avg_cost=avg,
                currency=currency,
                asset_id=hit.asset_id,
                note=note,
            )
            return {
                "ok": True,
                "action": "created",
                "holding": _holding_payload(created),
                "resolved": search_result_to_dict(hit),
                "marketQuote": quote,
            }
        new_qty, new_avg = weighted_avg_cost(existing.qty, existing.avg_cost, qty, avg)
        updated = ctx.holdings.update_holding(
            user_id,
            hit.asset_type,
            hit.symbol,
            qty=new_qty,
            avg_cost=new_avg,
            currency=currency,
            asset_id=hit.asset_id or existing.asset_id,
            note=note,
            note_provided=note is not None,
        )
        return {
            "ok": True,
            "action": "increased",
            "holding": _holding_payload(updated),
            "addedQty": format(qty, "f"),
            "resolved": search_result_to_dict(hit),
            "marketQuote": quote,
        }
    except DuplicateHoldingError as exc:
        raise ToolError(exc.detail) from exc
    except HoldingsValidationError as exc:
        raise ToolError(exc.detail) from exc


def remove_holding(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    query = _arg_str(args, "symbol", "query")
    if not query:
        raise ToolError("symbol is required")
    asset_type = _guess_asset_type(args)
    user_id = ctx.user.user_id

    record = None
    if asset_type:
        try:
            record = ctx.holdings.get_holding(user_id, asset_type, query)
        except (HoldingNotFoundError, HoldingsValidationError):
            record = None
    if record is None:
        listed = ctx.holdings.list_holdings(user_id)
        low = query.lower()
        matches = [
            h
            for h in listed
            if h.symbol.lower() == low
            or (h.asset_id or "").lower() == low
            or (asset_type and h.asset_type == asset_type and h.symbol.lower() == low)
        ]
        if len(matches) == 1:
            record = matches[0]
        elif len(matches) > 1:
            raise ToolError(
                "Multiple holdings match; pass assetType (crypto or stock) as well as symbol"
            )
        else:
            try:
                hit = resolve_asset(ctx, query, asset_type)
                record = ctx.holdings.get_holding(user_id, hit.asset_type, hit.symbol)
            except HoldingNotFoundError as exc:
                raise ToolError(exc.detail) from exc
            except ToolError:
                raise ToolError(f"Holding not found: {query}") from None

    qty_raw = args.get("qty")
    if qty_raw not in (None, ""):
        from app.services.llm.qty import parse_decimal

        reduce_by = parse_decimal(qty_raw, "qty")
        if reduce_by <= 0:
            raise ToolError("qty to remove must be greater than 0")
        remaining = record.qty - reduce_by
        if remaining > 0:
            updated = ctx.holdings.update_holding(
                user_id,
                record.asset_type,
                record.symbol,
                qty=remaining,
            )
            return {
                "ok": True,
                "action": "reduced",
                "holding": _holding_payload(updated),
                "removedQty": format(reduce_by, "f"),
            }
    ctx.holdings.delete_holding(user_id, record.asset_type, record.symbol)
    return {
        "ok": True,
        "action": "deleted",
        "symbol": record.symbol,
        "assetType": record.asset_type,
    }


def list_holdings(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _ = args
    items = ctx.holdings.list_holdings(ctx.user.user_id)
    return {"ok": True, "holdings": [_holding_payload(h) for h in items]}


def get_portfolio(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    display = _arg_str(args, "displayCurrency", "display_currency", "currency")
    asset_type = _guess_asset_type(args)
    try:
        view = ctx.portfolio.get_portfolio(
            ctx.user.user_id,
            display_currency=display,
            preferred_currency=ctx.user.preferred_currency,
            asset_type=asset_type,
            force_refresh=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise ToolError(str(getattr(exc, "detail", None) or exc)) from exc
    return {"ok": True, "portfolio": _portfolio_payload(view)}


def get_quote(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    query = _arg_str(args, "symbol", "query", "q")
    if not query:
        raise ToolError("symbol is required")
    hit = resolve_asset(ctx, query, _guess_asset_type(args))
    quote = _quote_for(ctx, hit)
    if quote is None:
        raise ToolError(f"No quote for {hit.symbol}")
    return {"ok": True, "resolved": search_result_to_dict(hit), "quote": quote}


def _history_summary(history: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not history:
        return None
    points = history.get("points") or []
    prices: list[float] = []
    for point in points:
        if not isinstance(point, dict) or point.get("price") is None:
            continue
        try:
            prices.append(float(point["price"]))
        except (TypeError, ValueError):
            continue
    if not prices:
        return {"range": history.get("range"), "points": 0}
    start, end = prices[0], prices[-1]
    change = ((end - start) / start * 100.0) if start else None
    return {
        "range": history.get("range"),
        "points": len(prices),
        "start": start,
        "end": end,
        "min": min(prices),
        "max": max(prices),
        "changePercent": change,
    }


def analyze_asset(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    query = _arg_str(args, "query", "symbol", "q") or ""
    hit = resolve_asset(ctx, query, _guess_asset_type(args))
    detail = None
    if ctx.asset_detail is not None:
        try:
            detail = ctx.asset_detail.get_detail(
                asset_type=hit.asset_type,
                slug=hit.symbol,
                currency=ctx.user.preferred_currency,
                range_="7d",
                preferred_currency=ctx.user.preferred_currency,
            )
        except (AssetNotFoundError, Exception):  # noqa: BLE001
            detail = None
    quote = None
    if detail and detail.get("quote"):
        quote = detail["quote"]
    else:
        quote = _quote_for(ctx, hit)
    news_items: list[dict[str, Any]] = []
    if ctx.news is not None:
        try:
            for item in ctx.news.list_for_user(ctx.user, limit=20):
                if hit.symbol.lower() in (item.title or "").lower() or hit.symbol.lower() in [
                    s.lower() for s in (item.symbols or [])
                ]:
                    news_items.append(_news_item_to_dict(item))
                if len(news_items) >= 5:
                    break
        except Exception:  # noqa: BLE001
            news_items = []
    profile = (detail or {}).get("profile") if detail else None
    payload = {
        "resolved": search_result_to_dict(hit),
        "quote": quote,
        "profile": profile,
        "history": _history_summary((detail or {}).get("history") if detail else None),
        "news": news_items,
        "preferredCurrency": ctx.user.preferred_currency,
    }
    analysis = None
    if ctx.run_analyst is not None:
        try:
            analysis = ctx.run_analyst("asset", payload)
        except Exception as exc:  # noqa: BLE001
            analysis = None
            # Do not forward provider internals, credentials, or exception
            # payloads into the next model turn.
            payload["analystError"] = "Analysis is temporarily unavailable."
    return {"ok": True, "analysis": analysis, "data": payload}


def analyze_portfolio(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    port = get_portfolio(args, ctx)
    news_items: list[dict[str, Any]] = []
    if ctx.news is not None:
        try:
            news_items = [_news_item_to_dict(i) for i in ctx.news.list_for_user(ctx.user, limit=8)]
        except Exception:  # noqa: BLE001
            news_items = []
    payload = {
        "portfolio": port.get("portfolio"),
        "news": news_items,
        "preferredCurrency": ctx.user.preferred_currency,
    }
    analysis = None
    if ctx.run_analyst is not None:
        try:
            analysis = ctx.run_analyst("portfolio", payload)
        except Exception as exc:  # noqa: BLE001
            analysis = None
            payload["analystError"] = "Analysis is temporarily unavailable."
    return {"ok": True, "analysis": analysis, "data": payload}


def get_news(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    if ctx.news is None:
        raise ToolError("News service is not available")
    limit_raw = args.get("limit") or 10
    try:
        limit = max(1, min(int(limit_raw), 25))
    except (TypeError, ValueError):
        limit = 10
    items = [_news_item_to_dict(i) for i in ctx.news.list_for_user(ctx.user, limit=limit)]
    return {"ok": True, "news": items}


def add_watchlist(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    query = _arg_str(args, "symbol", "query")
    if not query:
        raise ToolError("symbol is required")
    hit = resolve_asset(ctx, query, _guess_asset_type(args))
    try:
        item = ctx.watchlist.add_item(
            ctx.user.user_id,
            asset_type=hit.asset_type,
            symbol=hit.symbol,
            asset_id=hit.asset_id,
        )
    except DuplicateWatchlistError as exc:
        raise ToolError(exc.detail) from exc
    except WatchlistValidationError as exc:
        raise ToolError(exc.detail) from exc
    return {
        "ok": True,
        "action": "added",
        "symbol": item.symbol,
        "assetType": item.asset_type,
        "assetId": item.asset_id,
    }


def remove_watchlist(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    query = _arg_str(args, "symbol", "query")
    if not query:
        raise ToolError("symbol is required")
    asset_type = _guess_asset_type(args)
    try:
        if asset_type:
            ctx.watchlist.remove_item(ctx.user.user_id, asset_type, query)
            return {"ok": True, "action": "removed", "symbol": query.upper(), "assetType": asset_type}
        hit = resolve_asset(ctx, query, None)
        ctx.watchlist.remove_item(ctx.user.user_id, hit.asset_type, hit.symbol)
        return {
            "ok": True,
            "action": "removed",
            "symbol": hit.symbol,
            "assetType": hit.asset_type,
        }
    except WatchlistNotFoundError as exc:
        raise ToolError(exc.detail) from exc
    except WatchlistValidationError as exc:
        raise ToolError(exc.detail) from exc


def _schema(description: str, properties: dict[str, Any], required: Optional[list[str]] = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": _OBJECT,
        "properties": properties,
        "additionalProperties": True,
    }
    if required:
        body["required"] = required
    return body


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    specs = [
        ToolSpec(
            name="search_assets",
            description="Search crypto or VN stocks by name or symbol (bitcoin, BTC, FPT).",
            parameters=_schema(
                "",
                {
                    "q": {"type": _STRING, "description": "Search text"},
                    "assetType": {
                        "type": _STRING,
                        "enum": ["crypto", "stock"],
                        "description": "Optional type filter",
                    },
                },
                ["q"],
            ),
            handler=search_assets,
        ),
        ToolSpec(
            name="add_holding",
            description=(
                "Add or increase a holding. Use amount+price for notional buys "
                "(10 USD of BTC at 50000 → qty 0.0002). Existing positions are increased "
                "with weighted average cost."
            ),
            parameters=_schema(
                "",
                {
                    "symbol": {"type": _STRING, "description": "Symbol or name (BTC, bitcoin, FPT)"},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                    "qty": {"type": _STRING, "description": "Units to add (number as string)"},
                    "price": {"type": _STRING, "description": "Per-unit cost (alias of avgCost)"},
                    "avgCost": {"type": _STRING},
                    "amount": {
                        "type": _STRING,
                        "description": "Notional spend; qty = amount / price",
                    },
                    "currency": {"type": _STRING, "description": "USD or VND"},
                    "note": {"type": _STRING},
                },
                ["symbol"],
            ),
            handler=add_holding,
            mutating=True,
        ),
        ToolSpec(
            name="remove_holding",
            description="Remove a holding, or pass qty to reduce the position.",
            parameters=_schema(
                "",
                {
                    "symbol": {"type": _STRING},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                    "qty": {"type": _STRING, "description": "Optional units to sell"},
                },
                ["symbol"],
            ),
            handler=remove_holding,
            mutating=True,
        ),
        ToolSpec(
            name="list_holdings",
            description="List the user's holdings (no live valuation).",
            parameters=_schema("", {}),
            handler=list_holdings,
        ),
        ToolSpec(
            name="get_portfolio",
            description="Valued portfolio (prices, PnL, allocation) for this user.",
            parameters=_schema(
                "",
                {
                    "displayCurrency": {"type": _STRING},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                },
            ),
            handler=get_portfolio,
        ),
        ToolSpec(
            name="get_quote",
            description="Current cache-first price for a crypto or stock.",
            parameters=_schema(
                "",
                {
                    "symbol": {"type": _STRING},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                },
                ["symbol"],
            ),
            handler=get_quote,
        ),
        ToolSpec(
            name="analyze_asset",
            description=(
                "On-demand specialist: gather quote/profile/news for a coin or stock "
                "and write an analysis. Use for 'Analyze bitcoin'."
            ),
            parameters=_schema(
                "",
                {
                    "query": {"type": _STRING, "description": "Asset name or symbol"},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                },
                ["query"],
            ),
            handler=analyze_asset,
        ),
        ToolSpec(
            name="analyze_portfolio",
            description="On-demand specialist: value the user's book and explain PnL/risk.",
            parameters=_schema(
                "",
                {"displayCurrency": {"type": _STRING}},
            ),
            handler=analyze_portfolio,
        ),
        ToolSpec(
            name="get_news",
            description="Recent news filtered by the user's holdings, watchlist, and keywords.",
            parameters=_schema("", {"limit": {"type": _NUMBER}}),
            handler=get_news,
        ),
        ToolSpec(
            name="add_watchlist",
            description="Add a symbol to the user's watchlist.",
            parameters=_schema(
                "",
                {
                    "symbol": {"type": _STRING},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                },
                ["symbol"],
            ),
            handler=add_watchlist,
            mutating=True,
        ),
        ToolSpec(
            name="remove_watchlist",
            description="Remove a symbol from the user's watchlist.",
            parameters=_schema(
                "",
                {
                    "symbol": {"type": _STRING},
                    "assetType": {"type": _STRING, "enum": ["crypto", "stock"]},
                },
                ["symbol"],
            ),
            handler=remove_watchlist,
            mutating=True,
        ),
    ]
    for spec in specs:
        registry.register(spec)
    return registry


__all__ = [
    "ToolError",
    "build_default_registry",
    "resolve_asset",
]
