"""vnstock adapter package (fixture mode default; real HTTP later)."""

from app.adapters.vnstock.client import FixtureVnstockClient

__all__ = ["FixtureVnstockClient"]
