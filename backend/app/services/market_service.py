"""Market application service: search + cache-first quote resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from app.domain.models import PriceQuote
from app.ports.market import (
    AssetSearchResult,
    CryptoMarketClient,
    MarketDataError,
    StockMarketClient,
)
from app.ports.price_cache import PriceCacheRepo

DEFAULT_PRICE_CACHE_TTL_SECONDS = 600


class ValidationError(Exception):
    """Client input failed validation (maps to HTTP 400)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


_ALLOWED_TYPES = frozenset({"crypto", "stock"})


@dataclass(frozen=True)
class QuoteKey:
    """Request key for ``get_quotes``.

    Cache key is always ``(asset_type, symbol)``.
    For crypto, ``asset_id`` (CoinGecko id) is preferred when calling the client;
    falls back to lowercased symbol when missing.
    """

    asset_type: str
    symbol: str
    asset_id: Optional[str] = None


def _normalize_type(asset_type: str) -> str:
    t = (asset_type or "").strip().lower()
    if t not in _ALLOWED_TYPES:
        raise ValidationError("type must be 'crypto' or 'stock'")
    return t


def _normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if not s:
        raise ValidationError("symbol is required")
    return s


def _crypto_quote_matches(quote: PriceQuote, miss: QuoteKey, coin_id: str) -> bool:
    """True when quote is this request (ticker or coin id), not a different coin."""
    qsym = quote.symbol.upper()
    if qsym == miss.symbol.upper():
        return True
    if qsym == coin_id.upper():
        return True
    aid = (miss.asset_id or "").strip()
    if aid and qsym == aid.upper():
        return True
    return False


def _parse_quote_key(item: QuoteKey | tuple) -> QuoteKey:
    if isinstance(item, QuoteKey):
        at = _normalize_type(item.asset_type)
        sym = _normalize_symbol(item.symbol)
        aid = (item.asset_id or None)
        if aid is not None:
            aid = str(aid).strip() or None
        return QuoteKey(asset_type=at, symbol=sym, asset_id=aid)
    if isinstance(item, tuple):
        if len(item) == 2:
            at, sym = item
            return QuoteKey(
                asset_type=_normalize_type(str(at)),
                symbol=_normalize_symbol(str(sym)),
            )
        if len(item) >= 3:
            at, sym, aid = item[0], item[1], item[2]
            return QuoteKey(
                asset_type=_normalize_type(str(at)),
                symbol=_normalize_symbol(str(sym)),
                asset_id=str(aid).strip() if aid else None,
            )
    raise ValidationError("invalid quote key")


class MarketService:
    """Orchestrates market clients + PriceCache (no AWS SDK, no raw HTTP)."""

    def __init__(
        self,
        crypto: CryptoMarketClient,
        stock: StockMarketClient,
        cache: PriceCacheRepo,
        *,
        default_ttl_seconds: int = DEFAULT_PRICE_CACHE_TTL_SECONDS,
    ) -> None:
        self._crypto = crypto
        self._stock = stock
        self._cache = cache
        self._ttl = int(default_ttl_seconds) if default_ttl_seconds > 0 else DEFAULT_PRICE_CACHE_TTL_SECONDS

    @property
    def default_ttl_seconds(self) -> int:
        return self._ttl

    def search(self, q: str, asset_type: str) -> list[AssetSearchResult]:
        """Search assets by type. Raises ``ValidationError`` on bad input."""
        query = (q or "").strip()
        if not query:
            raise ValidationError("q must not be empty")
        at = _normalize_type(asset_type)
        if at == "crypto":
            return list(self._crypto.search(query))
        return list(self._stock.search(query))

    def list_assets(
        self,
        asset_type: str,
        *,
        limit: int = 250,
    ) -> list[AssetSearchResult]:
        """Browse the full catalog for ``crypto`` or ``stock`` (capped)."""
        at = _normalize_type(asset_type)
        cap = max(1, min(int(limit), 2000))
        if at == "crypto":
            return list(self._crypto.list_all(limit=cap))
        return list(self._stock.list_all(limit=cap))

    def get_quotes(
        self,
        keys: Sequence[QuoteKey | tuple],
        *,
        force: bool = False,
        ttl_seconds: Optional[int] = None,
    ) -> list[PriceQuote]:
        """Resolve prices cache-first; batch-fetch misses by asset type.

        Args:
            keys: ``QuoteKey`` or ``(asset_type, symbol[, asset_id])`` entries.
            force: When True, skip fresh-cache short-circuit and re-fetch.
            ttl_seconds: Override default TTL when writing cache.

        Returns:
            List of ``PriceQuote`` in request order where a price was found.
            Missing symbols after fetch are omitted.

        Raises:
            MarketDataError: external failure and no stale cache for a miss batch
                that was required (if some keys still unsatisfied).
            ValidationError: bad asset type / empty symbol.
        """
        ttl = self._ttl if ttl_seconds is None else int(ttl_seconds)
        parsed = [_parse_quote_key(k) for k in keys]
        if not parsed:
            return []

        # Dedupe while preserving first-seen order for stable client batches.
        seen: set[tuple[str, str]] = set()
        unique: list[QuoteKey] = []
        for k in parsed:
            ck = (k.asset_type, k.symbol)
            if ck not in seen:
                seen.add(ck)
                unique.append(k)

        results: dict[tuple[str, str], PriceQuote] = {}
        misses: list[QuoteKey] = []

        for k in unique:
            if not force:
                cached = self._cache.get(k.asset_type, k.symbol, allow_expired=False)
                if cached is not None:
                    results[(k.asset_type, k.symbol)] = cached.to_quote(stale=False)
                    continue
            misses.append(k)

        if misses:
            self._fetch_and_cache(misses, results, ttl=ttl)

        # Preserve original request order (including duplicates → same quote).
        out: list[PriceQuote] = []
        for k in parsed:
            q = results.get((k.asset_type, k.symbol))
            if q is not None:
                out.append(q)
        return out

    def _fetch_and_cache(
        self,
        misses: list[QuoteKey],
        results: dict[tuple[str, str], PriceQuote],
        *,
        ttl: int,
    ) -> None:
        crypto_misses = [m for m in misses if m.asset_type == "crypto"]
        stock_misses = [m for m in misses if m.asset_type == "stock"]

        if crypto_misses:
            self._fetch_crypto(crypto_misses, results, ttl=ttl)
        if stock_misses:
            self._fetch_stock(stock_misses, results, ttl=ttl)

    def _fetch_crypto(
        self,
        misses: list[QuoteKey],
        results: dict[tuple[str, str], PriceQuote],
        *,
        ttl: int,
    ) -> None:
        # Prefer asset_id; fall back to lowercased symbol for fixture convenience.
        id_for: dict[str, list[QuoteKey]] = {}
        for m in misses:
            cid = (m.asset_id or m.symbol).strip().lower()
            id_for.setdefault(cid, []).append(m)

        try:
            quotes = self._crypto.get_simple_prices(list(id_for.keys()), vs="usd")
        except Exception as exc:
            # Last-good / stale cache fallback
            missing_after_stale: list[QuoteKey] = []
            for m in misses:
                stale = self._cache.get(m.asset_type, m.symbol, allow_expired=True)
                if stale is not None:
                    results[(m.asset_type, m.symbol)] = stale.to_quote(stale=True)
                else:
                    missing_after_stale.append(m)
            if missing_after_stale:
                detail = getattr(exc, "detail", None) or str(exc) or "Market data unavailable"
                raise MarketDataError(detail) from exc
            return

        # Index by ticker and by coin id (request key / uppercased id-as-symbol).
        by_symbol: dict[str, PriceQuote] = {}
        by_id: dict[str, PriceQuote] = {}
        for q in quotes:
            by_symbol[q.symbol.upper()] = q
            by_id[q.symbol.lower()] = q

        for coin_id, keys in id_for.items():
            quote = by_id.get(coin_id)
            if quote is None:
                for m in keys:
                    quote = by_symbol.get(m.symbol)
                    if quote is not None:
                        break
            # Single leftover quote is used only when it *is* this requested id
            # (never assign quotes[0] just because counts are 1).
            if quote is None and len(quotes) == 1:
                only = quotes[0]
                if only.symbol.lower() == coin_id or only.symbol.upper() in {
                    k.symbol for k in keys
                }:
                    quote = only
            if quote is None:
                continue
            for m in keys:
                if not _crypto_quote_matches(quote, m, coin_id):
                    continue
                # Normalize symbol to requested ticker for cache consistency
                stored = PriceQuote(
                    asset_type="crypto",
                    symbol=m.symbol,
                    price=quote.price,
                    currency=quote.currency,
                    as_of=quote.as_of,
                    stale=False,
                )
                self._cache.put(stored, ttl)
                results[(m.asset_type, m.symbol)] = stored

    def _fetch_stock(
        self,
        misses: list[QuoteKey],
        results: dict[tuple[str, str], PriceQuote],
        *,
        ttl: int,
    ) -> None:
        symbols = [m.symbol for m in misses]
        try:
            quotes = self._stock.get_prices(symbols)
        except Exception as exc:
            missing_after_stale: list[QuoteKey] = []
            for m in misses:
                stale = self._cache.get(m.asset_type, m.symbol, allow_expired=True)
                if stale is not None:
                    results[(m.asset_type, m.symbol)] = stale.to_quote(stale=True)
                else:
                    missing_after_stale.append(m)
            if missing_after_stale:
                detail = getattr(exc, "detail", None) or str(exc) or "Market data unavailable"
                raise MarketDataError(detail) from exc
            return

        by_symbol = {q.symbol.upper(): q for q in quotes}
        for m in misses:
            quote = by_symbol.get(m.symbol)
            if quote is None:
                continue
            stored = PriceQuote(
                asset_type="stock",
                symbol=m.symbol,
                price=quote.price,
                currency=quote.currency,
                as_of=quote.as_of,
                stale=False,
            )
            self._cache.put(stored, ttl)
            results[(m.asset_type, m.symbol)] = stored


def search_result_to_dict(r: AssetSearchResult) -> dict:
    """Serialize search result to camelCase API DTO."""
    return {
        "symbol": r.symbol,
        "name": r.name,
        "assetId": r.asset_id,
        "assetType": r.asset_type,
    }


def quote_to_dict(
    quote: PriceQuote,
    *,
    asset_id: Optional[str] = None,
    source: str = "cache-first",
) -> dict:
    """Serialize a quote for watchlist / asset / batch quote APIs."""
    as_of = quote.as_of.isoformat()
    if quote.as_of.tzinfo is None and not as_of.endswith("Z"):
        as_of = as_of + "Z"
    return {
        "assetType": quote.asset_type,
        "symbol": quote.symbol,
        "assetId": asset_id,
        "price": format(quote.price, "f"),
        "currency": quote.currency,
        "asOf": as_of,
        "stale": bool(quote.stale),
        "source": source,
    }


__all__ = [
    "MarketService",
    "QuoteKey",
    "ValidationError",
    "MarketDataError",
    "DEFAULT_PRICE_CACHE_TTL_SECONDS",
    "search_result_to_dict",
    "quote_to_dict",
]
