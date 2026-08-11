"""News read + keyword/symbol filter (no RSS HTTP)."""

from __future__ import annotations

from typing import Optional, Sequence

from app.ports.holdings import HoldingsRepo
from app.ports.news import NewsItem, NewsRepo
from app.ports.users import UserProfile
from app.ports.watchlist import WatchlistRepo


def _matches(item: NewsItem, needles: Sequence[str]) -> bool:
    if not needles:
        return True
    title = (item.title or "").lower()
    item_syms = {s.lower() for s in (item.symbols or [])}
    item_kw = {k.lower() for k in (item.keywords or [])}
    for n in needles:
        n_l = n.lower()
        if n_l in title or n_l in item_syms or n_l in item_kw:
            return True
    return False


class NewsService:
    def __init__(
        self,
        news_repo: NewsRepo,
        holdings_repo: Optional[HoldingsRepo] = None,
        watchlist_repo: Optional[WatchlistRepo] = None,
    ) -> None:
        self._news = news_repo
        self._holdings = holdings_repo
        self._watchlist = watchlist_repo

    def list_for_user(self, user: UserProfile, limit: int = 50) -> list[NewsItem]:
        items = self._news.list_recent(limit=max(limit, 200))
        needles: list[str] = list(user.news_keywords or [])
        if self._holdings is not None:
            for h in self._holdings.list(user.user_id):
                needles.append(h.symbol)
        if self._watchlist is not None:
            for w in self._watchlist.list(user.user_id):
                needles.append(w.symbol)
        # unique case-insensitive preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for n in needles:
            k = n.lower()
            if k not in seen and n.strip():
                seen.add(k)
                uniq.append(n.strip())

        if not uniq:
            # PRD demo: no keywords/symbols → recent unfiltered
            return items[:limit]

        filtered = [i for i in items if _matches(i, uniq)]
        return filtered[:limit]


__all__ = ["NewsService"]
