"""ExchangeRate-API adapter (HTTP only inside this package)."""

from app.adapters.exchangerate.client import HttpExchangeRateClient

__all__ = ["HttpExchangeRateClient"]
