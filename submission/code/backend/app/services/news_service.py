"""News read: search shared storage by market / asset keywords + recency."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from app.domain.market_news import (
    MarketKind,
    classify_markets,
    is_market_relevant,
    matches_asset_query,
)
from app.ports.holdings import HoldingsRepo
from app.ports.news import NewsItem, NewsRepo
from app.ports.users import UserProfile
from app.ports.watchlist import WatchlistRepo


def _matches(item: NewsItem, needles: Sequence[str]) -> bool:
    if not needles:
        return True
    title = (item.title or "").lower()
    item_syms = {s.lower() for s in (item.symbols or [])}
    for n in needles:
        n_l = n.lower()
        if n_l in title or n_l in item_syms:
            return True
    return False


def _item_time(item: NewsItem) -> datetime:
    if item.published_at is not None:
        dt = item.published_at
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    if item.date:
        try:
            return datetime.fromisoformat(item.date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


class NewsService:
    """Read API over the shared News store (scan/list → filter → sort by time)."""

    def __init__(
        self,
        news_repo: NewsRepo,
        holdings_repo: Optional[HoldingsRepo] = None,
        watchlist_repo: Optional[WatchlistRepo] = None,
    ) -> None:
        self._news = news_repo
        self._holdings = holdings_repo
        self._watchlist = watchlist_repo

    def _recent_pool(self, limit: int) -> list[NewsItem]:
        # Oversample so keyword/market filters still have enough candidates.
        return self._news.list_recent(limit=max(limit * 4, 200))

    def search(
        self,
        *,
        limit: int = 50,
        market: MarketKind | None = None,
        queries: Sequence[str] | None = None,
        since: datetime | None = None,
    ) -> list[NewsItem]:
        """Search stored news by optional market board, keywords, and time floor."""
        items = self._recent_pool(limit)
        q = [x for x in (queries or []) if (x or "").strip()]
        out: list[NewsItem] = []
        for item in items:
            if since is not None and _item_time(item) < since:
                continue
            if market is not None:
                kinds = classify_markets(item.title or "", symbols=item.symbols)
                if market not in kinds:
                    continue
            elif not is_market_relevant(item.title or "", symbols=item.symbols):
                continue
            if q and not matches_asset_query(
                item.title or "",
                symbols=item.symbols,
                queries=q,
            ):
                continue
            out.append(item)
            if len(out) >= limit:
                break

        # Prefer symbol-tagged rows within the filtered set (stable market board).
        tagged = [i for i in out if i.symbols]
        untagged = [i for i in out if not i.symbols]
        ranked = tagged + untagged
        return ranked[:limit]

    def list_market(self, limit: int = 50, *, market: MarketKind | None = None) -> list[NewsItem]:
        """Markets Top Stories: all market news, or stock/crypto board only."""
        return self.search(limit=limit, market=market)

    def list_for_asset(
        self,
        *,
        symbol: str,
        names: Sequence[str] | None = None,
        asset_id: str | None = None,
        asset_type: MarketKind | None = None,
        limit: int = 20,
    ) -> list[NewsItem]:
        """Asset detail: search storage by symbol / name / id tokens."""
        queries = [symbol, asset_id or "", *(names or [])]
        return self.search(limit=limit, market=asset_type, queries=queries)

    def list_for_user(self, user: UserProfile, limit: int = 50) -> list[NewsItem]:
        """Personalized slice for chat/tools (keywords + holdings + watchlist)."""
        items = self._recent_pool(limit)
        needles: list[str] = list(user.news_keywords or [])
        if self._holdings is not None:
            for h in self._holdings.list(user.user_id):
                needles.append(h.symbol)
        if self._watchlist is not None:
            for w in self._watchlist.list(user.user_id):
                needles.append(w.symbol)
        seen: set[str] = set()
        uniq: list[str] = []
        for n in needles:
            k = n.lower()
            if k not in seen and n.strip():
                seen.add(k)
                uniq.append(n.strip())

        if not uniq:
            return self.list_market(limit=limit)

        filtered = [i for i in items if _matches(i, uniq)]
        if not filtered:
            return self.list_market(limit=limit)
        return filtered[:limit]


__all__ = ["NewsService"]
