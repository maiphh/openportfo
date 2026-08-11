"""Fixture market clients for local/test (re-export adapters + aliases)."""

from __future__ import annotations

from app.adapters.coingecko.client import FixtureCoinGeckoClient
from app.adapters.vnstock.client import FixtureVnstockClient

# Sprint plan names
FixtureCryptoMarketClient = FixtureCoinGeckoClient
FixtureStockMarketClient = FixtureVnstockClient

__all__ = [
    "FixtureCryptoMarketClient",
    "FixtureStockMarketClient",
    "FixtureCoinGeckoClient",
    "FixtureVnstockClient",
]
