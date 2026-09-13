"""Unit tests for VN stock logo URL helper."""

from app.adapters.vnstock.logos import stock_logo_url


def test_stock_logo_url_uses_shared_cdn_not_favicon() -> None:
    assert (
        stock_logo_url("ACB", homepage="https://www.acb.com.vn")
        == "https://companiesmarketcap.com/img/company-logos/128/ACB.VN.png"
    )


def test_stock_logo_url_prefers_explicit_provider() -> None:
    assert (
        stock_logo_url("VNM", explicit="https://cdn.example/vnm.png")
        == "https://cdn.example/vnm.png"
    )
