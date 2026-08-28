"""Market-relevance helpers for shared news ingest and Top Stories.

Storage model (unchanged): one News table/list with title, symbols[], published_at/date.
Reads search that store by keyword substring + recency (demo-scale scan, then filter).
"""

from __future__ import annotations

from typing import Iterable, Literal, Sequence

MarketKind = Literal["stock", "crypto"]

# Shared "any market" keep-list for ingest (stock ∪ crypto ∪ broad trading).
STOCK_TITLE_NEEDLES: tuple[str, ...] = (
    "stock",
    "stocks",
    "share price",
    "shares",
    "equity",
    "equities",
    "chứng khoán",
    "chung khoan",
    "cổ phiếu",
    "co phieu",
    "cổ phần",
    "co phan",
    "vn-index",
    "vnindex",
    "vn index",
    "hose",
    "hnx",
    "upcom",
    "bluechip",
    "blue-chip",
    "nasdaq",
    "nyse",
    "dow jones",
    "s&p",
    "wall street",
    "securities",
    "brokerage",
    "bond market",
)

CRYPTO_TITLE_NEEDLES: tuple[str, ...] = (
    "crypto",
    "cryptocurrency",
    "cryptocurrencies",
    "bitcoin",
    "btc",
    "ethereum",
    "ether",
    "blockchain",
    "altcoin",
    "stablecoin",
    "defi",
    "web3",
    "tokenomics",
    "coingecko",
)

BROAD_MARKET_NEEDLES: tuple[str, ...] = (
    "ipo",
    "etf",
    "forex",
    "bull market",
    "bear market",
    "market rally",
    "market crash",
    "stock market",
    "markets",
    "trading",
)

MARKET_TITLE_NEEDLES: tuple[str, ...] = (
    *STOCK_TITLE_NEEDLES,
    *CRYPTO_TITLE_NEEDLES,
    *BROAD_MARKET_NEEDLES,
)


def _normalize_needles(needles: Sequence[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in needles:
        text = " ".join((raw or "").split()).casefold()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


_STOCK_NEEDLES = _normalize_needles(STOCK_TITLE_NEEDLES)
_CRYPTO_NEEDLES = _normalize_needles(CRYPTO_TITLE_NEEDLES)
_MARKET_NEEDLES = _normalize_needles(MARKET_TITLE_NEEDLES)


def title_matches_needles(title: str, needles: Sequence[str]) -> bool:
    hay = (title or "").casefold()
    if not hay:
        return False
    for needle in needles:
        if needle and needle.casefold() in hay:
            return True
    return False


def is_market_relevant(
    title: str,
    *,
    symbols: Iterable[str] | None = None,
) -> bool:
    """True when the story is about markets (equities/crypto/trading) or tagged."""
    if any((s or "").strip() for s in (symbols or [])):
        return True
    return title_matches_needles(title, _MARKET_NEEDLES)


def _symbol_hints_crypto(symbols: Iterable[str] | None) -> bool:
    cryptoish = {
        "btc",
        "eth",
        "bitcoin",
        "ethereum",
        "sol",
        "xrp",
        "ada",
        "doge",
        "bnb",
        "usdt",
        "usdc",
    }
    for raw in symbols or []:
        key = (raw or "").strip().casefold()
        if key in cryptoish:
            return True
    return False


def _symbol_hints_stock(symbols: Iterable[str] | None) -> bool:
    """VN-style tickers are typically 3–4 Latin letters."""
    for raw in symbols or []:
        text = (raw or "").strip()
        if len(text) in (3, 4) and text.isalpha() and not _symbol_hints_crypto([text]):
            return True
    return False


def classify_markets(
    title: str,
    *,
    symbols: Iterable[str] | None = None,
) -> set[MarketKind]:
    """Which market boards this headline belongs on (may be both or empty)."""
    kinds: set[MarketKind] = set()
    if title_matches_needles(title, _STOCK_NEEDLES) or _symbol_hints_stock(symbols):
        kinds.add("stock")
    if title_matches_needles(title, _CRYPTO_NEEDLES) or _symbol_hints_crypto(symbols):
        kinds.add("crypto")
    return kinds


def matches_asset_query(
    title: str,
    *,
    symbols: Iterable[str] | None = None,
    queries: Sequence[str],
) -> bool:
    """Match stored news by symbol tags or title tokens (symbol / name / id)."""
    stored = {(s or "").strip().casefold() for s in (symbols or []) if (s or "").strip()}
    needles: list[str] = []
    for raw in queries:
        text = " ".join((raw or "").split())
        if not text:
            continue
        if text.casefold() in stored:
            return True
        needles.append(text)
    return title_matches_needles(title, needles)


__all__ = [
    "BROAD_MARKET_NEEDLES",
    "CRYPTO_TITLE_NEEDLES",
    "MARKET_TITLE_NEEDLES",
    "MarketKind",
    "STOCK_TITLE_NEEDLES",
    "classify_markets",
    "is_market_relevant",
    "matches_asset_query",
    "title_matches_needles",
]
