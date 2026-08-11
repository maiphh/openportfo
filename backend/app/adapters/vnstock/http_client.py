"""Live vnstock client with fixture fallback when library/network fails.

MARKET_CLIENT_MODE=http. Unit tests keep FixtureVnstockClient.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from app.adapters.vnstock.client import FixtureVnstockClient
from app.domain.models import PriceQuote
from app.ports.market import AssetSearchResult, MarketDataError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HttpVnstockClient:
    """Best-effort vnstock wrapper; falls back to fixtures on import/runtime failure."""

    def __init__(self, *, use_fixture_fallback: bool = True) -> None:
        self._fallback = FixtureVnstockClient() if use_fixture_fallback else None
        self._live = None
        try:
            # Lazy optional dependency — may be absent in Lambda thin package
            import vnstock  # type: ignore  # noqa: F401

            self._live = True
        except Exception:
            self._live = False

    def search(self, q: str) -> list[AssetSearchResult]:
        if not self._live and self._fallback is not None:
            return self._fallback.search(q)
        # vnstock search APIs vary by version; use fixture search for stability
        # when live listing is unavailable
        if self._fallback is not None:
            return self._fallback.search(q)
        return []

    def get_prices(self, symbols: Sequence[str]) -> list[PriceQuote]:
        if not symbols:
            return []
        if not self._live:
            if self._fallback is not None:
                return self._fallback.get_prices(symbols)
            raise MarketDataError("vnstock not available")

        out: list[PriceQuote] = []
        now = _utc_now()
        try:
            from vnstock import Vnstock  # type: ignore

            for sym in symbols:
                key = str(sym).upper()
                try:
                    stock = Vnstock().stock(symbol=key, source="VCI")
                    df = stock.quote.history(
                        start=(now.date().replace(day=1)).isoformat(),
                        end=now.date().isoformat(),
                        interval="1D",
                    )
                    if df is None or len(df) == 0:
                        continue
                    # last close
                    close_col = "close" if "close" in df.columns else df.columns[-1]
                    price = Decimal(str(df.iloc[-1][close_col]))
                    out.append(
                        PriceQuote(
                            asset_type="stock",
                            symbol=key,
                            price=price,
                            currency="VND",
                            as_of=now,
                        )
                    )
                except Exception:
                    continue
        except Exception as exc:
            if self._fallback is not None:
                return self._fallback.get_prices(symbols)
            raise MarketDataError(f"vnstock prices failed: {exc}") from exc

        if not out and self._fallback is not None:
            return self._fallback.get_prices(symbols)
        return out

    def get_history(self, symbol: str, range: str) -> list:
        if self._fallback is not None:
            return self._fallback.get_history(symbol, range)
        return []


__all__ = ["HttpVnstockClient"]
