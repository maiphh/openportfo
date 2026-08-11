"""Sprint 05: PortfolioService aggregates holdings + prices via domain math."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.models import PriceQuote
from app.ports.fx import StoredRates
from app.ports.holdings import HoldingRecord
from app.services.market_service import MarketService
from app.services.portfolio_service import (
    PortfolioService,
    ValidationError,
    holding_record_to_domain,
)
from tests.fakes.fx import InMemoryExchangeRateRepo
from tests.fakes.holdings import InMemoryHoldingsRepo
from tests.fakes.market import FixtureCryptoMarketClient, FixtureStockMarketClient
from tests.fakes.price_cache import InMemoryPriceCacheRepo


def _now() -> datetime:
    return datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _holding(
    *,
    user_id: str = "alice",
    asset_type: str = "crypto",
    symbol: str = "BTC",
    asset_id: str | None = "bitcoin",
    qty: str = "1",
    avg_cost: str = "30000",
    currency: str = "USD",
) -> HoldingRecord:
    return HoldingRecord(
        user_id=user_id,
        asset_type=asset_type,  # type: ignore[arg-type]
        symbol=symbol,
        qty=Decimal(qty),
        avg_cost=Decimal(avg_cost),
        currency=currency,
        asset_id=asset_id,
    )


def _svc(
    *,
    holdings: InMemoryHoldingsRepo | None = None,
    crypto: FixtureCryptoMarketClient | None = None,
    stock: FixtureStockMarketClient | None = None,
    cache: InMemoryPriceCacheRepo | None = None,
    fx: InMemoryExchangeRateRepo | None = None,
) -> tuple[
    PortfolioService,
    InMemoryHoldingsRepo,
    FixtureCryptoMarketClient,
    FixtureStockMarketClient,
    InMemoryPriceCacheRepo,
    InMemoryExchangeRateRepo,
]:
    h = holdings or InMemoryHoldingsRepo()
    c = crypto or FixtureCryptoMarketClient(
        prices={"bitcoin": (Decimal("40000"), "USD")},
    )
    s = stock or FixtureStockMarketClient(
        prices={"VNM": (Decimal("80000"), "VND")},
    )
    p = cache or InMemoryPriceCacheRepo()
    f = fx if fx is not None else InMemoryExchangeRateRepo()
    market = MarketService(c, s, p, default_ttl_seconds=600)
    return PortfolioService(h, market, fx_repo=f), h, c, s, p, f


# ---------------------------------------------------------------------------
# 1. One holding → correct totals (fakes)
# ---------------------------------------------------------------------------


def test_one_holding_correct_totals() -> None:
    """qty=1, avg=30000, price=40000 → MV=40000, cost=30000, pnl=10000."""
    svc, holdings, crypto, _, _, _ = _svc()
    holdings.create(_holding(qty="1", avg_cost="30000"))

    view = svc.get_portfolio("alice")

    assert len(view.summary.lines) == 1
    line = view.summary.lines[0]
    assert line.market_value == Decimal("40000")
    assert line.cost_basis == Decimal("30000")
    assert line.pnl == Decimal("10000")
    assert line.pnl_percent == Decimal("10000") / Decimal("30000")
    assert line.missing_price is False
    usd = view.summary.totals_by_currency["USD"]
    assert usd.market_value == Decimal("40000")
    assert usd.cost_basis == Decimal("30000")
    assert usd.pnl == Decimal("10000")
    assert crypto.price_calls == 1


def test_holding_record_maps_to_domain() -> None:
    rec = _holding()
    rec.note = "n1"
    d = holding_record_to_domain(rec)
    assert d.user_id == "alice"
    assert d.symbol == "BTC"
    assert d.qty == Decimal("1")
    assert d.asset_id == "bitcoin"
    assert d.note == "n1"


# ---------------------------------------------------------------------------
# 2. Mixed USD/VND native subtotals
# ---------------------------------------------------------------------------


def test_mixed_usd_vnd_native_subtotals() -> None:
    svc, holdings, _, _, _, _ = _svc()
    holdings.create(_holding(symbol="BTC", qty="1", avg_cost="30000", currency="USD"))
    holdings.create(
        _holding(
            asset_type="stock",
            symbol="VNM",
            asset_id="VNM",
            qty="100",
            avg_cost="70000",
            currency="VND",
        )
    )

    view = svc.get_portfolio("alice")

    assert len(view.summary.lines) == 2
    usd = view.summary.totals_by_currency["USD"]
    vnd = view.summary.totals_by_currency["VND"]
    assert usd.market_value == Decimal("40000")
    assert usd.cost_basis == Decimal("30000")
    assert usd.pnl == Decimal("10000")
    assert vnd.market_value == Decimal("8000000")
    assert vnd.cost_basis == Decimal("7000000")
    assert vnd.pnl == Decimal("1000000")
    # No display conversion without rates + display currency
    assert view.summary.market_value_display is None
    assert view.summary.fx_status == "missing"


# ---------------------------------------------------------------------------
# 3. Refresh invokes market client
# ---------------------------------------------------------------------------


def test_refresh_invokes_market_client() -> None:
    svc, holdings, crypto, stock, cache, _ = _svc()
    holdings.create(_holding())
    # Warm cache first
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("39000"),
            currency="USD",
            as_of=_now(),
        ),
        600,
    )
    # GET uses cache
    view1 = svc.get_portfolio("alice", force_refresh=False)
    assert view1.summary.lines[0].price == Decimal("39000")
    assert crypto.price_calls == 0

    # force refresh hits client
    view2 = svc.get_portfolio("alice", force_refresh=True)
    assert crypto.price_calls == 1
    assert view2.summary.lines[0].price == Decimal("40000")


# ---------------------------------------------------------------------------
# 4. GET warm cache → market not called
# ---------------------------------------------------------------------------


def test_get_warm_cache_skips_market_client() -> None:
    cache = InMemoryPriceCacheRepo()
    cache.put(
        PriceQuote(
            asset_type="crypto",
            symbol="BTC",
            price=Decimal("42000"),
            currency="USD",
            as_of=_now(),
        ),
        600,
    )
    svc, holdings, crypto, stock, _, _ = _svc(cache=cache)
    holdings.create(_holding())

    view = svc.get_portfolio("alice", force_refresh=False)

    assert view.summary.lines[0].price == Decimal("42000")
    assert crypto.price_calls == 0
    assert stock.price_calls == 0


# ---------------------------------------------------------------------------
# 5. ExchangeRateClient never present / never called
# ---------------------------------------------------------------------------


def test_portfolio_service_has_no_fx_http_client() -> None:
    """Service constructor accepts only holdings, market, fx_repo — no client."""
    sig = inspect.signature(PortfolioService.__init__)
    names = set(sig.parameters) - {"self"}
    assert "fx_repo" in names
    assert "exchange_rate_client" not in names
    assert "fx_client" not in names
    assert "client" not in names


def test_get_portfolio_reads_fx_repo_not_http() -> None:
    """get_latest may be called; no ExchangeRateClient exists on service."""
    fx = InMemoryExchangeRateRepo()
    fx.seed(
        StoredRates(
            base="USD",
            rates={
                "USD_VND": Decimal("25000"),
                "VND_USD": Decimal("0.00004"),
            },
            as_of=_now(),
            status="fresh",
            provider="test",
        )
    )
    svc, holdings, _, _, _, _ = _svc(fx=fx)
    holdings.create(_holding(qty="1", avg_cost="30000"))

    view = svc.get_portfolio("alice", display_currency="VND")

    assert fx.get_latest_calls == 1
    assert view.summary.fx_status == "fresh"
    assert view.summary.market_value_display == Decimal("1000000000")  # 40000 * 25000
    assert "USD_VND" in view.fx_rates
    # Prove no client attribute
    assert not hasattr(svc, "_fx_client")
    assert not hasattr(svc, "exchange_rate_client")


def test_apply_fx_uses_domain_math_only() -> None:
    """Mixed portfolio converted with S01 fixture numbers."""
    fx = InMemoryExchangeRateRepo()
    fx.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=_now(),
            status="fresh",
        )
    )
    svc, holdings, _, _, _, _ = _svc(fx=fx)
    holdings.create(_holding(qty="1", avg_cost="30000", currency="USD"))
    holdings.create(
        _holding(
            asset_type="stock",
            symbol="VNM",
            asset_id="VNM",
            qty="100",
            avg_cost="70000",
            currency="VND",
        )
    )

    view = svc.get_portfolio("alice", display_currency="VND")
    s = view.summary
    assert s.market_value_display == Decimal("1008000000")
    assert s.cost_basis_display == Decimal("757000000")
    assert s.pnl_display == Decimal("251000000")


# ---------------------------------------------------------------------------
# Filter + empty + missing FX
# ---------------------------------------------------------------------------


def test_filter_asset_type_crypto() -> None:
    svc, holdings, crypto, stock, _, _ = _svc()
    holdings.create(_holding(symbol="BTC", asset_type="crypto"))
    holdings.create(
        _holding(
            asset_type="stock",
            symbol="VNM",
            asset_id="VNM",
            qty="100",
            avg_cost="70000",
            currency="VND",
        )
    )

    view = svc.get_portfolio("alice", asset_type="crypto")
    assert len(view.summary.lines) == 1
    assert view.summary.lines[0].symbol == "BTC"
    assert "USD" in view.summary.totals_by_currency
    assert "VND" not in view.summary.totals_by_currency
    assert crypto.price_calls == 1
    assert stock.price_calls == 0


def test_filter_invalid_asset_type_raises() -> None:
    svc, _, _, _, _, _ = _svc()
    with pytest.raises(ValidationError, match="assetType"):
        svc.get_portfolio("alice", asset_type="forex")


def test_empty_portfolio() -> None:
    svc, _, crypto, stock, _, _ = _svc()
    view = svc.get_portfolio("alice")
    assert view.summary.lines == []
    assert view.summary.totals_by_currency == {}
    assert view.summary.fx_status == "missing"
    assert view.as_of is None
    assert crypto.price_calls == 0
    assert stock.price_calls == 0


def test_preferred_currency_triggers_fx_when_rates_present() -> None:
    fx = InMemoryExchangeRateRepo()
    fx.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=_now(),
            status="fresh",
        )
    )
    svc, holdings, _, _, _, _ = _svc(fx=fx)
    holdings.create(_holding(qty="1", avg_cost="30000"))

    view = svc.get_portfolio("alice", preferred_currency="VND")
    assert view.summary.display_currency == "VND"
    assert view.summary.market_value_display == Decimal("1000000000")


def test_no_duplicate_math_in_service_module() -> None:
    """Service must not re-implement pnl/market_value formulas."""
    import app.services.portfolio_service as mod

    src = inspect.getsource(mod)
    # Domain imports are required; local formula reimplementation is not
    assert "compute_native_portfolio" in src
    assert "apply_fx" in src
    # Crude guard: no qty * price style inline valuation in service body
    assert "holding.qty * " not in src
    assert "qty * price" not in src
