"""BL-027: ExportService CSV shape, FX conversion, missing FX (no HTTP)."""

from __future__ import annotations

import csv
import inspect
import io
from datetime import datetime, timezone
from decimal import Decimal

from app.domain.models import PortfolioLine, PortfolioSummary
from app.ports.fx import StoredRates
from app.ports.holdings import HoldingRecord
from app.services.export_service import CSV_HEADER, csv_filename, render_portfolio_csv
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService, PortfolioView
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
    fx: InMemoryExchangeRateRepo | None = None,
) -> tuple[PortfolioService, InMemoryHoldingsRepo, FixtureCryptoMarketClient, InMemoryExchangeRateRepo]:
    h = holdings or InMemoryHoldingsRepo()
    c = crypto or FixtureCryptoMarketClient(
        prices={"bitcoin": (Decimal("40000"), "USD")},
    )
    s = FixtureStockMarketClient(prices={"VNM": (Decimal("80000"), "VND")})
    p = InMemoryPriceCacheRepo()
    f = fx if fx is not None else InMemoryExchangeRateRepo()
    market = MarketService(c, s, p, default_ttl_seconds=600)
    return PortfolioService(h, market, fx_repo=f), h, c, f


def _rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    assert reader.fieldnames == CSV_HEADER
    return list(reader)


def test_empty_portfolio_header_only() -> None:
    view = PortfolioView(
        summary=PortfolioSummary(fx_status="missing"),
        fx_rates={},
        as_of=None,
    )
    text = render_portfolio_csv(view)
    assert text.startswith(",".join(CSV_HEADER))
    assert "\r\n" in text
    assert text.encode("utf-8")[:3] != b"\xef\xbb\xbf"
    data_rows = [ln for ln in text.split("\r\n") if ln][1:]
    assert data_rows == []
    assert _rows(text) == []


def test_one_btc_holding_math_matches_portfolio_service() -> None:
    svc, holdings, _, _ = _svc()
    holdings.create(_holding(qty="1", avg_cost="30000"))
    view = svc.get_portfolio("alice")
    line = view.summary.lines[0]
    assert line.market_value == Decimal("40000")
    assert line.cost_basis == Decimal("30000")
    assert line.pnl == Decimal("10000")
    assert line.pnl_percent == Decimal("10000") / Decimal("30000")

    text = render_portfolio_csv(view)
    assert text.endswith("\r\n") or "\r\n" in text
    rows = _rows(text)
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "BTC"
    assert row["assetType"] == "crypto"
    assert row["assetId"] == "bitcoin"
    assert Decimal(row["qty"]) == Decimal("1")
    assert Decimal(row["avgCost"]) == Decimal("30000")
    assert row["currency"] == "USD"
    assert Decimal(row["price"]) == Decimal("40000")
    assert Decimal(row["marketValue"]) == Decimal("40000")
    assert Decimal(row["costBasis"]) == Decimal("30000")
    assert Decimal(row["pnl"]) == Decimal("10000")
    assert Decimal(row["pnlPercent"]) == line.pnl_percent
    assert Decimal(row["allocation"]) == Decimal("1") if row["allocation"] else (
        line.allocation is None
    )
    if line.allocation is not None:
        assert Decimal(row["allocation"]) == line.allocation


def test_display_columns_two_decimal_places() -> None:
    line = PortfolioLine(
        user_id="alice",
        asset_type="crypto",
        symbol="BTC",
        qty=Decimal("1"),
        avg_cost=Decimal("30000"),
        currency="USD",
        asset_id="bitcoin",
        price=Decimal("40000"),
        market_value=Decimal("40000"),
        cost_basis=Decimal("30000"),
        pnl=Decimal("10000"),
        pnl_percent=Decimal("10000") / Decimal("30000"),
        display_currency="VND",
        avg_cost_display=Decimal("750000000"),
        price_display=Decimal("1000000000"),
        market_value_display=Decimal("1000000000"),
        cost_basis_display=Decimal("750000000"),
        pnl_display=Decimal("250000000"),
        allocation=Decimal("1"),
    )
    view = PortfolioView(
        summary=PortfolioSummary(
            lines=[line],
            display_currency="VND",
            fx_status="fresh",
        ),
        fx_rates={"USD_VND": Decimal("25000")},
        as_of=_now(),
    )
    row = _rows(render_portfolio_csv(view))[0]
    for col in (
        "avgCostDisplay",
        "priceDisplay",
        "marketValueDisplay",
        "costBasisDisplay",
        "pnlDisplay",
    ):
        assert "." in row[col]
        assert len(row[col].split(".")[-1]) == 2


def test_quoting_commas_and_quotes_and_crlf() -> None:
    line = PortfolioLine(
        user_id="alice",
        asset_type="crypto",
        symbol='BTC, "MAX"',
        qty=Decimal("1"),
        avg_cost=Decimal("1"),
        currency="USD",
        asset_id='id,with"quote',
        price=Decimal("1"),
        market_value=Decimal("1"),
        cost_basis=Decimal("1"),
        pnl=Decimal("0"),
    )
    view = PortfolioView(
        summary=PortfolioSummary(lines=[line], fx_status="missing"),
        fx_rates={},
        as_of=None,
    )
    text = render_portfolio_csv(view)
    assert "\r\n" in text
    assert "\n" not in text.replace("\r\n", "")
    row = _rows(text)[0]
    assert row["symbol"] == 'BTC, "MAX"'
    assert row["assetId"] == 'id,with"quote'
    # QUOTE_MINIMAL wraps delimiter/quotechar; doubled quotes inside the field
    assert '"BTC, ""MAX"""' in text


def test_csv_injection_prefix_on_symbol_only() -> None:
    line = PortfolioLine(
        user_id="alice",
        asset_type="crypto",
        symbol="=HYPERLINK",
        qty=Decimal("1"),
        avg_cost=Decimal("1"),
        currency="USD",
        asset_id="bitcoin",
        price=Decimal("2"),
        market_value=Decimal("2"),
        cost_basis=Decimal("1"),
        pnl=Decimal("-5000"),
    )
    view = PortfolioView(
        summary=PortfolioSummary(lines=[line], fx_status="missing"),
        fx_rates={},
        as_of=None,
    )
    text = render_portfolio_csv(view)
    row = _rows(text)[0]
    assert row["symbol"].startswith("'=")
    # Native numeric columns must not be formula-prefixed (user-controlled text only)
    assert row["pnl"] == format(Decimal("-5000"), "f")


def test_csv_filename_utc_yyyymmdd() -> None:
    name = csv_filename(datetime(2026, 8, 23, 1, 2, 3, tzinfo=timezone.utc))
    assert name == "openportfo-portfolio-20260823.csv"


def test_portfolio_export_fx_conversion() -> None:
    """AC2: stored USD→VND rate converts display columns (same path as PortfolioService)."""
    fx = InMemoryExchangeRateRepo()
    fx.seed(
        StoredRates(
            base="USD",
            rates={"USD_VND": Decimal("25000")},
            as_of=_now(),
            status="fresh",
            provider="seed",
        )
    )
    svc, holdings, _, _ = _svc(fx=fx)
    holdings.create(_holding())
    view = svc.get_portfolio("alice", display_currency="VND")
    assert view.summary.fx_status == "fresh"
    assert view.summary.market_value_display == Decimal("1000000000")
    line = view.summary.lines[0]
    assert line.avg_cost_display == Decimal("750000000")
    assert line.price_display == Decimal("1000000000")
    assert line.market_value_display == Decimal("1000000000")
    assert line.cost_basis_display == Decimal("750000000")

    row = _rows(render_portfolio_csv(view))[0]
    assert Decimal(row["marketValue"]) == Decimal("40000")
    assert Decimal(row["costBasis"]) == Decimal("30000")
    assert Decimal(row["marketValueDisplay"]) == Decimal("1000000000")
    assert Decimal(row["costBasisDisplay"]) == Decimal("750000000")
    assert Decimal(row["avgCostDisplay"]) == Decimal("750000000")
    assert Decimal(row["fxRateUsed"]) == Decimal("25000")
    assert row["fxStatus"] == "fresh"
    assert row["currency_display"] == "VND"


def test_missing_fx_native_filled_converted_blank() -> None:
    """AC3: no stored rate + display != native → native filled, converted blank, fxStatus=missing."""
    svc, holdings, _, fx_repo = _svc()
    holdings.create(_holding())
    view = svc.get_portfolio("alice", display_currency="VND")
    assert view.summary.fx_status == "missing"
    line = view.summary.lines[0]
    assert line.market_value == Decimal("40000")
    assert line.market_value_display is None

    row = _rows(render_portfolio_csv(view))[0]
    assert Decimal(row["qty"]) == Decimal("1")
    assert Decimal(row["avgCost"]) == Decimal("30000")
    assert Decimal(row["price"]) == Decimal("40000")
    assert Decimal(row["marketValue"]) == Decimal("40000")
    assert Decimal(row["costBasis"]) == Decimal("30000")
    assert Decimal(row["pnl"]) == Decimal("10000")
    assert row["avgCostDisplay"] == ""
    assert row["priceDisplay"] == ""
    assert row["marketValueDisplay"] == ""
    assert row["costBasisDisplay"] == ""
    assert row["pnlDisplay"] == ""
    assert row["fxStatus"] == "missing"
    assert fx_repo.get_latest_calls >= 1


def test_export_service_has_no_http_or_aws_imports() -> None:
    import app.services.export_service as export_svc

    src = inspect.getsource(export_svc)
    assert "ExchangeRateClient" not in src
    assert "boto3" not in src
    assert "botocore" not in src
    assert "httpx" not in src
    assert "requests" not in src
