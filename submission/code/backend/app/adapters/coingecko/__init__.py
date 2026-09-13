"""CoinGecko adapter package (fixture mode default; real HTTP later)."""

from app.adapters.coingecko.client import FixtureCoinGeckoClient

__all__ = ["FixtureCoinGeckoClient"]
