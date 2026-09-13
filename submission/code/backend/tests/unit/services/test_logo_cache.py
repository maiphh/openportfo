"""Logo cache unit tests."""

from app.services.logo_cache import LogoCache


def test_logo_cache_round_trip_and_key_normalization() -> None:
    cache = LogoCache()
    cache.put("crypto", "BTC", "https://example.com/btc.png")
    assert cache.get("crypto", "btc") == "https://example.com/btc.png"
    cache.put("stock", "acb", "https://example.com/acb.png")
    assert cache.get("stock", "ACB") == "https://example.com/acb.png"


def test_logo_cache_ignores_blank_urls() -> None:
    cache = LogoCache()
    cache.put("crypto", "ETH", "  ")
    assert cache.get("crypto", "ETH") is None
