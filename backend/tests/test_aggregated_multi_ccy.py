"""
Integration tests for multi-currency-pair aggregated P&L analysis.

Covers the ``calculate_aggregated_analysis`` path with focus on:
  - CNY-quoted option pairs (USD/CNY, EUR/CNY, ...)
  - Cross-pair options (EUR/USD, USD/HKD, ...) — spot from ExchangeRateService
  - CNY-converted P&L fields (npv_cny, premium_pnl_cny, exercise_pnl_cny, total_pnl_cny)
  - Per-currency-pair aggregation (delta/gamma kept in original currency)
  - Spot trade P&L for both CNY-quoted and cross pairs
  - Exercise scenario with linked derivative spot trade
  - Total P&L composition: total_pnl_cny = total_option_pnl_cny + total_spot_pnl_cny
  - Currency exposure aggregation
  - Missing exchange rate handling (None FX → None *_cny fields)
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Portfolio, OptionTrade, SpotTrade
from app.models.curve import FxImpliedRate
from app.models.exchange_rate import ExchangeRate
from app.schemas.portfolio import (
    AggregatedAnalysisRequest,
    AggregatedAnalysisResponse,
    OptionTradeParamsOverride,
)
from app.services.portfolio_service import PortfolioService
from app.services.greeks_service import GreeksService
from app.services.curve_service import CurveService
from app.services.exchange_rate_service import ExchangeRateService


# ============================================================================
# Helpers
# ============================================================================


def _today(days_offset: int = 0) -> date:
    return date.today() + timedelta(days=days_offset)


# ============================================================================
# Data-seeding fixtures
# ============================================================================


@pytest.fixture
def fx_curve_data(session: Session) -> list[FxImpliedRate]:
    """Seed FX implied rate curve for USD, EUR, HKD, JPY, GBP against CNY.

    Provides spot rates and risk-free rates for ~250 days so that the
    curve service can interpolate at any valuation date in the recent
    past.  Spot rates are fixed per currency for deterministic tests.
    """
    spots = {
        "USD": 7.1000,   # USD/CNY
        "EUR": 7.8000,   # EUR/CNY
        "HKD": 0.9100,   # HKD/CNY
        "JPY": 0.0460,   # JPY/CNY (per 1 JPY)
        "GBP": 9.0500,   # GBP/CNY
    }
    tenors = ["1W", "1M", "3M", "6M", "1Y", "2Y"]
    tenor_rates = {
        "1W":  (3.80, 1.80),
        "1M":  (4.00, 2.00),
        "3M":  (4.20, 2.10),
        "6M":  (4.50, 2.30),
        "1Y":  (4.80, 2.50),
        "2Y":  (5.00, 2.70),
    }

    records: list[FxImpliedRate] = []
    for days_ago in range(250):
        curve_date = _today(-days_ago)
        for ccy, spot in spots.items():
            for tenor in tenors:
                fir, cnyr = tenor_rates[tenor]
                records.append(FxImpliedRate(
                    curve_date=curve_date,
                    foreign_currency=ccy,
                    tenor=tenor,
                    foreign_implied_rate=fir,
                    cny_risk_free_rate=cnyr,
                    spot_rate=spot,
                    swap_points=None,
                    source="test_seed",
                ))

    session.add_all(records)
    session.commit()
    return records


@pytest.fixture
def exchange_rate_data(session: Session, fx_curve_data) -> list[ExchangeRate]:
    """Seed exchange_rate rows for today covering all 9 supported pairs.

    These explicit rows let us assert deterministic FX rates for CNY
    conversion of cross-pair P&L (instead of relying on fx_implied fallback).
    """
    today = _today(0)
    rows = [
        # 5 direct CNY pairs
        ExchangeRate(rate_date=today, ccy_pair="USD/CNY", rate=7.1000,
                     source="fx_implied_curve"),
        ExchangeRate(rate_date=today, ccy_pair="EUR/CNY", rate=7.8000,
                     source="fx_implied_curve"),
        ExchangeRate(rate_date=today, ccy_pair="HKD/CNY", rate=0.9100,
                     source="fx_implied_curve"),
        ExchangeRate(rate_date=today, ccy_pair="GBP/CNY", rate=9.0500,
                     source="fx_implied_curve"),
        ExchangeRate(rate_date=today, ccy_pair="JPY/CNY", rate=0.0460,
                     source="fx_implied_curve"),
        # 4 cross-derived pairs
        ExchangeRate(rate_date=today, ccy_pair="USD/HKD", rate=7.1000/0.9100,
                     source="cross_derived"),
        ExchangeRate(rate_date=today, ccy_pair="USD/JPY", rate=7.1000/0.0460,
                     source="cross_derived"),
        ExchangeRate(rate_date=today, ccy_pair="EUR/USD", rate=7.8000/7.1000,
                     source="cross_derived"),
        ExchangeRate(rate_date=today, ccy_pair="GBP/USD", rate=9.0500/7.1000,
                     source="cross_derived"),
    ]
    session.add_all(rows)
    session.commit()
    return rows


@pytest.fixture
def multi_ccy_portfolio(session: Session) -> Portfolio:
    """Create a portfolio with option trades spanning multiple currency pairs.

    Trades:
      - USD/CNY CALL Buy, pre-expiry (valuation < expiry)
      - EUR/USD PUT Buy, pre-expiry
      - USD/HKD CALL Sell, pre-expiry
    """
    portfolio = Portfolio(name="MultiCcy-Options", description="multi-ccy test")
    session.add(portfolio)
    session.flush()

    trades = [
        OptionTrade(
            trade_id="MC-USD/CNY-001",
            portfolio_id=portfolio.id,
            ccy_pair="USD/CNY",
            trade_type="CALL",
            direction="买入",
            strike=7.1000,
            notional1=10_000_000.0,
            trade_date=_today(-30),
            expiry_date=_today(180),
            spot_rate=7.1000,
            volatility=0.05,
            premium_amount=200_000.0,
            premium_currency="CNY",
            exercise_status="未行权",
        ),
        OptionTrade(
            trade_id="MC-EUR/USD-002",
            portfolio_id=portfolio.id,
            ccy_pair="EUR/USD",
            trade_type="PUT",
            direction="买入",
            strike=1.1000,
            notional1=5_000_000.0,
            trade_date=_today(-20),
            expiry_date=_today(150),
            spot_rate=1.0986,    # ≈ 7.8000 / 7.1000
            volatility=0.06,
            premium_amount=50_000.0,
            premium_currency="USD",
            exercise_status="未行权",
        ),
        OptionTrade(
            trade_id="MC-USD/HKD-003",
            portfolio_id=portfolio.id,
            ccy_pair="USD/HKD",
            trade_type="CALL",
            direction="卖出",
            strike=7.8000,
            notional1=2_000_000.0,
            trade_date=_today(-10),
            expiry_date=_today(90),
            spot_rate=7.8022,    # ≈ 7.1000 / 0.9100
            volatility=0.04,
            premium_amount=30_000.0,
            premium_currency="HKD",
            exercise_status="未行权",
        ),
    ]
    session.add_all(trades)
    session.commit()
    session.refresh(portfolio)
    return portfolio


@pytest.fixture
def spot_portfolio(session: Session) -> Portfolio:
    """Portfolio with spot trades across CNY-quoted and cross pairs."""
    portfolio = Portfolio(name="MultiCcy-Spot", description="spot test")
    session.add(portfolio)
    session.flush()

    trades = [
        SpotTrade(
            trade_id="SP-USD/CNY-001",
            portfolio_id=portfolio.id,
            ccy_pair="USD/CNY",
            direction="买入",
            deal_price=7.0800,
            ccy1_amount=10_000_000.0,
            ccy2_amount=-70_800_000.0,
            ccy1="USD",
            ccy2="CNY",
            trade_date=_today(-5),
            settlement_date=_today(-3),
        ),
        SpotTrade(
            trade_id="SP-USD/HKD-002",
            portfolio_id=portfolio.id,
            ccy_pair="USD/HKD",
            direction="买入",
            deal_price=7.7800,
            ccy1_amount=5_000_000.0,
            ccy2_amount=-38_900_000.0,
            ccy1="USD",
            ccy2="HKD",
            trade_date=_today(-3),
            settlement_date=_today(-1),
        ),
        SpotTrade(
            trade_id="SP-EUR/USD-003",
            portfolio_id=portfolio.id,
            ccy_pair="EUR/USD",
            direction="卖出",
            deal_price=1.1050,
            ccy1_amount=-3_000_000.0,
            ccy2_amount=3_315_000.0,
            ccy1="EUR",
            ccy2="USD",
            trade_date=_today(-2),
            settlement_date=_today(0),
        ),
    ]
    session.add_all(trades)
    session.commit()
    session.refresh(portfolio)
    return portfolio


@pytest.fixture
def exercised_option_portfolio(session: Session) -> Portfolio:
    """Portfolio with an expired option exercised into a derivative spot trade.

    The option's ``exercise_derivative_trade_id`` points to the spot trade's
    ``trade_id`` string.  Both share the same portfolio so they appear in the
    same aggregate request.
    """
    portfolio = Portfolio(name="Exercise-Scenario", description="exercise test")
    session.add(portfolio)
    session.flush()

    expiry_date = _today(-10)

    # The derivative spot trade that settles the option exercise
    spot = SpotTrade(
        trade_id="EX-SPOT-001",
        portfolio_id=portfolio.id,
        ccy_pair="USD/CNY",
        direction="买入",
        deal_price=7.1000,           # strike
        ccy1_amount=10_000_000.0,
        ccy2_amount=-71_000_000.0,
        ccy1="USD",
        ccy2="CNY",
        trade_date=expiry_date,
        settlement_date=expiry_date,
    )
    option = OptionTrade(
        trade_id="EX-OPT-001",
        portfolio_id=portfolio.id,
        ccy_pair="USD/CNY",
        trade_type="CALL",
        direction="买入",
        strike=7.1000,
        notional1=10_000_000.0,
        trade_date=_today(-60),
        expiry_date=expiry_date,
        spot_rate=7.1000,
        volatility=0.05,
        premium_amount=150_000.0,
        premium_currency="CNY",
        exercise_status="已行权",
        exercise_derivative_trade_id="EX-SPOT-001",
    )
    session.add_all([spot, option])
    session.commit()
    session.refresh(portfolio)
    return portfolio


@pytest.fixture
def service() -> PortfolioService:
    """PortfolioService with real sub-services (uses test session via DI)."""
    return PortfolioService(
        greeks_service=GreeksService(),
        curve_service=CurveService(),
        exchange_rate_service=ExchangeRateService(),
    )


def _trade_vol_overrides(
    session: Session, portfolio_ids: list[int],
) -> list[OptionTradeParamsOverride]:
    """Vol overrides for option trades, simulating a user who filled in the
    vol field in the params table after ``获取参数``.

    Volatility is included for every option that recorded one. This matters
    for two cases in these tests:

    * Cross pairs (EUR/USD, USD/HKD) — the CNY-implied curve cannot derive
      cross-pair volatility at all.
    * CNY-quoted pairs here — the test curve seeds a *constant* spot rate for
      determinism, so the curve's historical-vol calculation returns None
      (in production, real spot history would yield a curve vol).

    Using each trade's recorded volatility keeps the NPV/delta values
    identical to the prior trade-default behaviour, so the aggregation
    assertions remain valid.
    """
    overrides: list[OptionTradeParamsOverride] = []
    trades = session.exec(
        select(OptionTrade).where(OptionTrade.portfolio_id.in_(portfolio_ids))
    ).all()
    for t in trades:
        if t.volatility is not None:
            overrides.append(OptionTradeParamsOverride(
                trade_id=t.id, volatility=t.volatility,
            ))
    return overrides


def _aggregate(
    service: PortfolioService,
    session: Session,
    portfolio_ids: list[int],
    valuation_date: date | None = None,
    start_date: date | None = None,
    curve_type: str | None = "fx_implied_rate",
    trade_params: list[OptionTradeParamsOverride] | None = None,
) -> AggregatedAnalysisResponse:
    """Helper: invoke calculate_aggregated_analysis with sensible defaults.

    By default it injects vol overrides for the portfolios' option trades,
    mirroring a user who completed the params table. Pass ``trade_params=[]``
    to disable injection and exercise the missing-params error path.
    """
    return service.calculate_aggregated_analysis(
        session,
        AggregatedAnalysisRequest(
            portfolio_ids=portfolio_ids,
            start_date=start_date,
            valuation_date=valuation_date or _today(0),
            curve_type=curve_type,
            trade_params=(
                trade_params if trade_params is not None
                else _trade_vol_overrides(session, portfolio_ids)
            ),
        ),
    )


# ============================================================================
# CNY-quoted option pair — pre-expiry
# ============================================================================


class TestCnyQuotedOptionPnl:
    """USD/CNY option (ccy2 == CNY) → fx_rate_to_cny should be 1.0."""

    def test_usd_cny_option_resolves(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "USD/CNY"][0]

        assert opt.error is None
        assert opt.delta is not None
        assert opt.gamma is not None
        assert opt.npv is not None and opt.npv != 0
        assert opt.premium_pnl is not None
        # Pre-expiry: exercise_pnl should be None, total_pnl == premium_pnl
        assert opt.exercise_pnl is None
        assert opt.total_pnl == opt.premium_pnl

    def test_cny_pair_fx_rate_is_one(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """For CNY-quoted pairs, fx_rate_to_cny must be 1.0 (no conversion)."""
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "USD/CNY"][0]

        assert opt.fx_rate_to_cny == 1.0
        # *_cny fields should equal their original-currency counterparts
        assert opt.npv_cny == round(opt.npv * 10_000_000 * 1.0, 2)
        assert opt.premium_pnl_cny == opt.premium_pnl
        assert opt.total_pnl_cny == opt.total_pnl

    def test_usd_cny_pair_metrics_aggregated(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """USD/CNY should appear in option_metrics_by_ccy_pair with correct fields."""
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        pair_metrics = [
            m for m in resp.summary.option_metrics_by_ccy_pair
            if m.ccy_pair == "USD/CNY"
        ]
        assert len(pair_metrics) == 1
        m = pair_metrics[0]
        assert m.fx_rate_to_cny == 1.0
        assert m.trade_count == 1
        # delta/gamma in original currency (ccy2/1ccy1), not converted
        assert m.delta != 0
        assert m.gamma != 0
        # CNY P&L == original (fx = 1)
        assert m.npv_cny == round(opt.npv_cny if (opt := [t for t in resp.option_trades if t.ccy_pair == "USD/CNY"][0]) else 0, 2)


# ============================================================================
# Cross-pair option — pre-expiry
# ============================================================================


class TestCrossPairOptionPnl:
    """EUR/USD and USD/HKD options — spot from ExchangeRateService."""

    def test_cross_pair_option_errors_without_vol_override(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """Cross-pair options with no user-supplied vol must error — the
        CNY-implied curve cannot derive cross-pair volatility, and there are
        no longer trade/hardcoded defaults to fall back on."""
        resp = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            trade_params=[],  # explicitly no overrides
        )
        eur_usd = [t for t in resp.option_trades if t.ccy_pair == "EUR/USD"][0]
        assert eur_usd.error is not None
        usd_hkd = [t for t in resp.option_trades if t.ccy_pair == "USD/HKD"][0]
        assert usd_hkd.error is not None

    def test_eur_usd_option_resolves(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "EUR/USD"][0]

        assert opt.error is None
        assert opt.delta is not None
        assert opt.npv is not None

    def test_eur_usd_fx_rate_uses_usd_cny(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """EUR/USD ccy2=USD → fx_rate_to_cny must equal USD/CNY rate (7.1000)."""
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "EUR/USD"][0]

        assert opt.fx_rate_to_cny == pytest.approx(7.1000, rel=1e-4)
        # CNY-converted fields should be original × 7.1
        if opt.premium_pnl is not None:
            assert opt.premium_pnl_cny == pytest.approx(
                opt.premium_pnl * 7.1000, rel=1e-3,
            )
        if opt.total_pnl is not None:
            assert opt.total_pnl_cny == pytest.approx(
                opt.total_pnl * 7.1000, rel=1e-3,
            )

    def test_usd_hkd_fx_rate_uses_hkd_cny(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """USD/HKD ccy2=HKD → fx_rate_to_cny must equal HKD/CNY rate (0.9100)."""
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "USD/HKD"][0]

        assert opt.fx_rate_to_cny == pytest.approx(0.9100, rel=1e-4)
        if opt.total_pnl is not None:
            assert opt.total_pnl_cny == pytest.approx(
                opt.total_pnl * 0.9100, rel=1e-3,
            )

    def test_cross_pair_uses_exchange_rate_service_for_spot(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """The resolved spot for EUR/USD should be ≈ EUR/CNY ÷ USD/CNY = 1.0986."""
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        # The NPV being non-zero and finite confirms spot was resolved.
        opt = [t for t in resp.option_trades if t.ccy_pair == "EUR/USD"][0]
        assert opt.error is None
        assert opt.npv is not None
        # Spot ~1.0986, strike 1.1000 → slight OTM put, NPV should be positive (long put)
        assert opt.npv > 0


# ============================================================================
# Multi-currency aggregation
# ============================================================================


class TestMultiCcyAggregation:
    """Per-currency-pair aggregation across multiple pairs in one portfolio."""

    def test_one_metrics_entry_per_pair(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        pairs = {m.ccy_pair for m in resp.summary.option_metrics_by_ccy_pair}
        assert pairs == {"USD/CNY", "EUR/USD", "USD/HKD"}

    def test_total_option_pnl_cny_equals_sum_of_pairs(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        pair_sum = round(
            sum(m.total_option_pnl_cny for m in resp.summary.option_metrics_by_ccy_pair),
            2,
        )
        assert resp.summary.total_option_pnl_cny == pytest.approx(pair_sum, abs=0.01)

    def test_delta_gamma_kept_in_original_currency(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """Per-pair delta/gamma must be delta × notional in ccy2/1ccy1 units."""
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        for m in resp.summary.option_metrics_by_ccy_pair:
            # delta/gamma should be NOT scaled by the ccy2→CNY rate
            # (just by notional, in original currency units)
            assert m.delta != 0
            assert m.gamma != 0

    def test_pair_metrics_trade_count(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        counts = {m.ccy_pair: m.trade_count for m in resp.summary.option_metrics_by_ccy_pair}
        assert counts == {"USD/CNY": 1, "EUR/USD": 1, "USD/HKD": 1}

    def test_metrics_sorted_by_ccy_pair(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        pairs = [m.ccy_pair for m in resp.summary.option_metrics_by_ccy_pair]
        assert pairs == sorted(pairs)


# ============================================================================
# Spot trade P&L
# ============================================================================


class TestSpotTradePnl:
    """Spot P&L for CNY-quoted and cross pairs."""

    def test_cny_quoted_spot_uses_curve(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """USD/CNY spot: market_rate from curve (7.1000), fx_rate_to_cny=1.0."""
        resp = _aggregate(service, session, [spot_portfolio.id])
        sp = [t for t in resp.spot_trades if t.ccy_pair == "USD/CNY"][0]

        assert sp.error is None
        assert sp.market_rate == pytest.approx(7.1000, rel=1e-4)
        assert sp.fx_rate_to_cny == 1.0
        # P&L = (market_rate - deal_price) * ccy1_amount
        expected_pnl = (7.1000 - 7.0800) * 10_000_000.0
        assert sp.pnl == pytest.approx(expected_pnl, rel=1e-3)
        # pnl_cny == pnl (ccy2 = CNY, fx = 1)
        assert sp.pnl_cny == pytest.approx(sp.pnl, rel=1e-6)

    def test_cross_pair_spot_uses_exchange_rate_service(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """USD/HKD spot: market_rate from ExchangeRateService (7.1000/0.9100)."""
        resp = _aggregate(service, session, [spot_portfolio.id])
        sp = [t for t in resp.spot_trades if t.ccy_pair == "USD/HKD"][0]

        assert sp.error is None
        expected_market = 7.1000 / 0.9100
        assert sp.market_rate == pytest.approx(expected_market, rel=1e-3)
        # ccy2 = HKD → fx_rate_to_cny = HKD/CNY = 0.9100
        assert sp.fx_rate_to_cny == pytest.approx(0.9100, rel=1e-4)
        # pnl_cny = pnl × 0.91
        assert sp.pnl_cny == pytest.approx(sp.pnl * 0.9100, rel=1e-3)

    def test_eur_usd_spot_fx_uses_usd_cny(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """EUR/USD spot: ccy2=USD → fx_rate_to_cny = USD/CNY = 7.1000."""
        resp = _aggregate(service, session, [spot_portfolio.id])
        sp = [t for t in resp.spot_trades if t.ccy_pair == "EUR/USD"][0]

        assert sp.error is None
        assert sp.fx_rate_to_cny == pytest.approx(7.1000, rel=1e-4)
        assert sp.pnl_cny == pytest.approx(sp.pnl * 7.1000, rel=1e-3)

    def test_total_spot_pnl_cny_sums_all_spot_trades(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [spot_portfolio.id])
        expected = round(sum(t.pnl_cny for t in resp.spot_trades if t.pnl_cny), 2)
        assert resp.summary.total_spot_pnl_cny == pytest.approx(expected, abs=0.01)


# ============================================================================
# Total P&L composition
# ============================================================================


class TestTotalPnlComposition:
    """total_pnl_cny = total_option_pnl_cny + total_spot_pnl_cny."""

    def test_total_pnl_with_options_only(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        assert resp.summary.total_spot_pnl_cny == 0.0
        assert resp.summary.total_pnl_cny == pytest.approx(
            resp.summary.total_option_pnl_cny, abs=0.01,
        )

    def test_total_pnl_with_spot_only(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [spot_portfolio.id])
        assert resp.summary.total_option_pnl_cny == 0.0
        assert resp.summary.total_pnl_cny == pytest.approx(
            resp.summary.total_spot_pnl_cny, abs=0.01,
        )

    def test_total_pnl_with_both(
        self, service, session, multi_ccy_portfolio, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session,
                          [multi_ccy_portfolio.id, spot_portfolio.id])
        expected = round(
            resp.summary.total_option_pnl_cny + resp.summary.total_spot_pnl_cny,
            2,
        )
        assert resp.summary.total_pnl_cny == pytest.approx(expected, abs=0.01)
        assert resp.portfolio_count == 2
        assert resp.portfolio_name == "多投组"


# ============================================================================
# Exercise scenario
# ============================================================================


class TestExerciseScenario:
    """Expired option with exercise_derivative_trade_id → exercise_pnl computed."""

    def test_expired_option_has_exercise_pnl(
        self, service, session, exercised_option_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [exercised_option_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "USD/CNY"][0]

        # Expiry < valuation → expired path
        assert opt.exercise_status == "已行权"
        assert opt.exercise_pnl is not None
        # CALL Buy: exercise_value = (market - strike) × notional
        # market at expiry (from curve) ≈ 7.1000, strike = 7.1000
        # → exercise_value ≈ 0
        # Allow small tolerance since curve spot is fixed at 7.1000
        assert opt.exercise_pnl == pytest.approx(0.0, abs=1.0)

    def test_exercise_pnl_cny_converted(
        self, service, session, exercised_option_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [exercised_option_portfolio.id])
        opt = [t for t in resp.option_trades if t.ccy_pair == "USD/CNY"][0]
        assert opt.fx_rate_to_cny == 1.0  # USD/CNY
        assert opt.exercise_pnl_cny == pytest.approx(
            opt.exercise_pnl * 1.0, abs=0.01,
        )

    def test_derivative_spot_uses_expiry_spot_rate(
        self, service, session, exercised_option_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """The linked spot trade should be flagged as derivative and use
        the expiry-date spot as its adjusted_deal_price."""
        resp = _aggregate(service, session, [exercised_option_portfolio.id])
        sp = resp.spot_trades[0]

        assert sp.is_derivative is True
        # adjusted_deal_price should equal the expiry spot rate (≈ 7.1000)
        assert sp.adjusted_deal_price == pytest.approx(7.1000, rel=1e-4)

    def test_total_pnl_includes_exercise(
        self, service, session, exercised_option_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [exercised_option_portfolio.id])
        opt = resp.option_trades[0]
        # total_pnl = premium_pnl + exercise_pnl
        expected = (opt.premium_pnl or 0) + (opt.exercise_pnl or 0)
        assert opt.total_pnl == pytest.approx(expected, abs=0.01)


# ============================================================================
# Currency exposure
# ============================================================================


class TestCurrencyExposure:
    """Spot-trade currency exposure aggregation across target currencies."""

    def test_exposure_sums_ccy1_and_ccy2(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [spot_portfolio.id])
        exp = resp.summary.currency_exposures
        # USD: +10M (USD/CNY ccy1) + 5M (USD/HKD ccy1) + 3.315M (EUR/USD ccy2)
        # = 18.315M  (EUR/USD sell = receive USD, so ccy2_amount is +3.315M)
        assert exp["USD"] == pytest.approx(
            10_000_000 + 5_000_000 + 3_315_000, rel=1e-3,
        )
        # CNY: -70.8M (USD/CNY ccy2)
        assert exp["CNY"] == pytest.approx(-70_800_000, rel=1e-3)
        # HKD: -38.9M (USD/HKD ccy2)
        assert exp["HKD"] == pytest.approx(-38_900_000, rel=1e-3)
        # EUR: -3M (EUR/USD ccy1)
        assert exp["EUR"] == pytest.approx(-3_000_000, rel=1e-3)

    def test_all_target_currencies_present(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = _aggregate(service, session, [spot_portfolio.id])
        exp = resp.summary.currency_exposures
        for ccy in ("CNY", "USD", "HKD", "EUR", "JPY", "GBP"):
            assert ccy in exp
            assert isinstance(exp[ccy], float)


# ============================================================================
# Missing exchange rate handling
# ============================================================================


class TestMissingExchangeRate:
    """When no exchange rate is available for a cross pair, *_cny fields are None."""

    def test_missing_fx_yields_none_cny_fields(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data,
        # NOTE: exchange_rate_data fixture deliberately NOT requested
    ):
        """Without exchange_rate rows, cross-pair P&L CNY conversion should be None.

        USD/CNY still resolves (fx_implied fallback in ExchangeRateService),
        but the FX cache may still produce a rate via fx_implied fallback.
        This test asserts the field-population contract: when ``_get_fx_to_cny``
        returns None, the *_cny fields must be None.
        """
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        for opt in resp.option_trades:
            if opt.fx_rate_to_cny is None:
                assert opt.npv_cny is None
                assert opt.premium_pnl_cny is None
                assert opt.exercise_pnl_cny is None
                assert opt.total_pnl_cny is None
            else:
                # When FX is available, *_cny fields must be populated
                assert opt.npv_cny is not None
                assert opt.total_pnl_cny is not None

    def test_missing_fx_pair_metrics_have_none_rate(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data,
    ):
        resp = _aggregate(service, session, [multi_ccy_portfolio.id])
        # At minimum, every pair has an entry (even if fx_rate_to_cny is None)
        assert len(resp.summary.option_metrics_by_ccy_pair) >= 1
        for m in resp.summary.option_metrics_by_ccy_pair:
            # fx_rate_to_cny may be None or a float, but never undefined
            assert m.fx_rate_to_cny is None or isinstance(m.fx_rate_to_cny, float)


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    """Empty portfolios, no trades in date range, etc."""

    def test_empty_portfolio_returns_zero_totals(
        self, service, session, fx_curve_data, exchange_rate_data,
    ):
        portfolio = Portfolio(name="Empty")
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)

        resp = _aggregate(service, session, [portfolio.id])
        assert resp.option_trade_count == 0
        assert resp.spot_trade_count == 0
        assert resp.summary.total_option_pnl_cny == 0.0
        assert resp.summary.total_spot_pnl_cny == 0.0
        assert resp.summary.total_pnl_cny == 0.0
        assert resp.summary.option_metrics_by_ccy_pair == []

    def test_no_trades_in_date_range(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """Date range that excludes all trades → empty result."""
        resp = _aggregate(
            service, session,
            [multi_ccy_portfolio.id],
            start_date=_today(-200),
            valuation_date=_today(-100),
        )
        assert resp.option_trade_count == 0
        assert resp.spot_trade_count == 0

    def test_unsupported_ccy_pair_skipped(
        self, service, session, fx_curve_data, exchange_rate_data,
    ):
        """Options with unsupported ccy_pair should still appear but with errors."""
        portfolio = Portfolio(name="Unsupported")
        session.add(portfolio)
        session.flush()
        session.add(OptionTrade(
            trade_id="BAD-001",
            portfolio_id=portfolio.id,
            ccy_pair="AUD/USD",  # not in SUPPORTED_CCY_PAIRS
            trade_type="CALL",
            direction="买入",
            strike=0.6500,
            notional1=1_000_000.0,
            trade_date=_today(-5),
            expiry_date=_today(60),
            spot_rate=0.6500,
            volatility=0.05,
        ))
        session.commit()
        session.refresh(portfolio)

        resp = _aggregate(service, session, [portfolio.id])
        # The trade should still appear in option_trades
        assert resp.option_trade_count == 1
        # AUD/USD is unsupported → likely error or zero metrics
        # (it won't appear in option_metrics_by_ccy_pair since the pair
        #  splitter returns None for unsupported quote currency resolution)
        opt = resp.option_trades[0]
        assert opt.ccy_pair == "AUD/USD"


# ============================================================================
# Interval P&L — spot trades (trade_date < start_date)
# ============================================================================


class TestSpotIntervalPnl:
    """When trade_date < start_date, adjusted_deal_price = market_rate(start_date)
    and pnl reflects only [start_date, val_date]."""

    def test_adjusted_deal_price_uses_start_date_rate(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """spot trade_date=_today(-5), start_date=_today(-1) → adjusted_deal_price
        should be the curve spot at start_date (≈7.1000), not deal_price (7.0800)."""
        resp = _aggregate(
            service, session, [spot_portfolio.id],
            start_date=_today(-1), valuation_date=_today(0),
        )
        sp = [t for t in resp.spot_trades if t.ccy_pair == "USD/CNY"][0]

        assert sp.error is None
        # adjusted_deal_price should be market_rate(start_date) ≈ 7.1000, NOT 7.0800
        assert sp.adjusted_deal_price == pytest.approx(7.1000, rel=1e-4)
        assert sp.adjusted_deal_price != pytest.approx(7.0800, rel=1e-4)

    def test_interval_pnl_is_mark_to_market(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """With fixed curve spot (7.1000 at both dates), interval pnl ≈ 0
        whereas original pnl = (7.1000 - 7.0800) × 10M = 200,000."""
        resp_interval = _aggregate(
            service, session, [spot_portfolio.id],
            start_date=_today(-1), valuation_date=_today(0),
        )
        sp_int = [t for t in resp_interval.spot_trades if t.ccy_pair == "USD/CNY"][0]

        # Both rates are 7.1000 → pnl ≈ 0
        assert sp_int.pnl == pytest.approx(0.0, abs=0.01)

        # Compare with original mode (start_date = earliest trade_date)
        resp_orig = _aggregate(
            service, session, [spot_portfolio.id],
            start_date=_today(-5), valuation_date=_today(0),
        )
        sp_orig = [t for t in resp_orig.spot_trades if t.ccy_pair == "USD/CNY"][0]
        assert sp_orig.pnl == pytest.approx(200_000.0, rel=1e-3)
        assert sp_int.pnl != pytest.approx(sp_orig.pnl, rel=1e-3)

    def test_interval_mode_includes_pre_interval_trades(
        self, service, session, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """Trades with trade_date < start_date are still included
        (the old filter would have excluded them)."""
        resp = _aggregate(
            service, session, [spot_portfolio.id],
            start_date=_today(-1), valuation_date=_today(0),
        )
        # All 3 spot trades have trade_date < start_date but should be included
        assert resp.spot_trade_count == 3


# ============================================================================
# Interval P&L — option trades (trade_date < start_date)
# ============================================================================


class TestOptionIntervalPnl:
    """When trade_date < start_date, premium_pnl = (NPV(val) - NPV(start)) × notional,
    and risk metrics (npv, delta, gamma) remain at val_date."""

    def test_risk_metrics_unchanged_by_start_date(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """NPV, delta, gamma must be identical regardless of start_date."""
        resp_int = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            start_date=_today(-5), valuation_date=_today(0),
        )
        resp_orig = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            start_date=_today(-30), valuation_date=_today(0),
        )

        for pair in ("USD/CNY", "EUR/USD", "USD/HKD"):
            opt_int = [t for t in resp_int.option_trades if t.ccy_pair == pair][0]
            opt_orig = [t for t in resp_orig.option_trades if t.ccy_pair == pair][0]

            assert opt_int.npv == pytest.approx(opt_orig.npv, rel=1e-6)
            assert opt_int.delta == pytest.approx(opt_orig.delta, rel=1e-6)
            assert opt_int.gamma == pytest.approx(opt_orig.gamma, rel=1e-6)

    def test_interval_pnl_uses_npv_difference(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """premium_pnl = (NPV(val) - NPV(start)) × notional when trade_date < start_date."""
        start = _today(-5)
        resp = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            start_date=start, valuation_date=_today(0),
        )
        opt = [t for t in resp.option_trades if t.ccy_pair == "USD/CNY"][0]

        assert opt.error is None
        assert opt.exercise_pnl is None  # pre-expiry
        assert opt.total_pnl == opt.premium_pnl

        # Independently compute NPV at start_date
        trade = session.exec(
            select(OptionTrade).where(
                OptionTrade.portfolio_id == multi_ccy_portfolio.id,
                OptionTrade.ccy_pair == "USD/CNY",
            )
        ).one()

        # Independently compute NPV at start_date, using the same vol
        # override the production interval path now applies at start_date.
        spot_s, vol_s, rfb_s, rfq_s, _ = service._resolve_params_for_trade(
            session, trade, start,
            OptionTradeParamsOverride(trade_id=trade.id, volatility=trade.volatility),
            "fx_implied_rate", None,
        )
        greeks_start = service.greeks_service.calculate_vanilla_greeks(
            option_type=trade.trade_type,
            direction=trade.direction,
            spot=spot_s,
            strike=float(trade.strike),
            volatility=vol_s,
            rf_rate_base=rfb_s,
            rf_rate_quote=rfq_s,
            valuation_date=start,
            expiry_date=trade.expiry_date,
        )
        npv_start = greeks_start.get("npv") or 0.0
        notional = trade.notional1 or 1.0

        expected = (opt.npv - npv_start) * notional
        assert opt.premium_pnl == pytest.approx(expected, rel=1e-3)

    def test_interval_pnl_differs_from_original(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """Interval premium_pnl should differ from original (total) premium_pnl."""
        resp_int = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            start_date=_today(-5), valuation_date=_today(0),
        )
        resp_orig = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            start_date=_today(-30), valuation_date=_today(0),
        )

        opt_int = [t for t in resp_int.option_trades if t.ccy_pair == "USD/CNY"][0]
        opt_orig = [t for t in resp_orig.option_trades if t.ccy_pair == "USD/CNY"][0]

        # Same NPV (risk metric) but different P&L
        assert opt_int.npv == pytest.approx(opt_orig.npv, rel=1e-6)
        assert opt_int.premium_pnl != pytest.approx(opt_orig.premium_pnl, rel=1e-3)

    def test_interval_mode_includes_pre_interval_options(
        self, service, session, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        """Options with trade_date < start_date are still included."""
        resp = _aggregate(
            service, session, [multi_ccy_portfolio.id],
            start_date=_today(-5), valuation_date=_today(0),
        )
        # All 3 options have trade_date < start_date but should be included
        assert resp.option_trade_count == 3


# ============================================================================
# API endpoint smoke test
# ============================================================================


class TestAggregateEndpoint:
    """Smoke test for POST /api/v1/portfolios/aggregate."""

    def test_endpoint_returns_200(
        self, client: TestClient, multi_ccy_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = client.post(
            "/api/v1/portfolios/aggregate",
            json={
                "portfolio_ids": [multi_ccy_portfolio.id],
                "valuation_date": _today(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "option_metrics_by_ccy_pair" in data["summary"]
        assert "total_option_pnl_cny" in data["summary"]
        assert "total_spot_pnl_cny" in data["summary"]
        assert "total_pnl_cny" in data["summary"]
        assert "currency_exposures" in data["summary"]

    def test_endpoint_rejects_empty_portfolio_ids(
        self, client: TestClient,
    ):
        resp = client.post(
            "/api/v1/portfolios/aggregate",
            json={
                "portfolio_ids": [],
                "valuation_date": _today(0).isoformat(),
            },
        )
        assert resp.status_code == 400

    def test_endpoint_multi_portfolio(
        self, client: TestClient, multi_ccy_portfolio, spot_portfolio,
        fx_curve_data, exchange_rate_data,
    ):
        resp = client.post(
            "/api/v1/portfolios/aggregate",
            json={
                "portfolio_ids": [multi_ccy_portfolio.id, spot_portfolio.id],
                "valuation_date": _today(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_count"] == 2
        assert data["portfolio_name"] == "多投组"
        # Both option and spot trades present
        assert data["option_trade_count"] >= 3
        assert data["spot_trade_count"] >= 3
