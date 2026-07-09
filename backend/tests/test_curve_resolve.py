"""
Integration tests for portfolio curve parameter resolution and Greeks calculation.

These tests use the test database (file-based SQLite) and seed real
FxImpliedRate data covering multiple dates, currencies, and tenors.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Portfolio, OptionTrade
from app.models.curve import FxImpliedRate


# ============================================================================
# Fixtures
# ============================================================================


def _make_date(days_ago: int = 0) -> date:
    """Return a date *days_ago* days before today."""
    return date.today() - timedelta(days=days_ago)


def _future_date(days_ahead: int) -> date:
    """Return a date *days_ahead* days after today."""
    return date.today() + timedelta(days=days_ahead)


@pytest.fixture
def portfolio_with_trades(session: Session) -> Portfolio:
    """Create a portfolio with two USD/CNY option trades (different expiries)."""
    portfolio = Portfolio(name="Test Portfolio", description="Curve test")
    session.add(portfolio)
    session.flush()

    t1 = OptionTrade(
        trade_id="CURVE-001",
        portfolio_id=portfolio.id,
        ccy_pair="USD/CNY",
        trade_type="CALL",
        direction="买入",
        strike=7.1200,
        notional1=10_000_000.0,
        expiry_date=_future_date(180),  # ~6 months out
        spot_rate=7.1150,
        volatility=0.0125,
    )
    t2 = OptionTrade(
        trade_id="CURVE-002",
        portfolio_id=portfolio.id,
        ccy_pair="USD/CNY",
        trade_type="PUT",
        direction="卖出",
        strike=7.0000,
        notional1=5_000_000.0,
        expiry_date=_future_date(365),  # ~12 months out
        spot_rate=7.1150,
        volatility=0.0125,
    )
    t3 = OptionTrade(
        trade_id="CURVE-003",
        portfolio_id=portfolio.id,
        ccy_pair="EUR/USD",  # non-CNY quote → should not resolve from curve
        trade_type="CALL",
        direction="买入",
        strike=1.1000,
        notional1=1_000_000.0,
        expiry_date=_future_date(180),
    )
    session.add_all([t1, t2, t3])
    session.commit()
    session.refresh(portfolio)
    return portfolio


@pytest.fixture
def fx_implied_rate_data(session: Session) -> list[FxImpliedRate]:
    """Seed realistic FxImpliedRate data for USD/CNY covering ~400 days.

    This provides:
    - Multiple tenors (1W, 1M, 3M, 6M, 1Y, 2Y) per date
    - Enough historical points for volatility calculation
    - Known values for testing interpolation
    """
    records: list[FxImpliedRate] = []
    tenors = ["1W", "1M", "3M", "6M", "1Y", "2Y"]
    # Rates per tenor (percentage values): foreign_implied_rate, cny_risk_free_rate
    tenor_rates: dict[str, tuple[float, float]] = {
        "1W": (3.80, 1.80),
        "1M": (4.00, 2.00),
        "3M": (4.20, 2.10),
        "6M": (4.50, 2.30),
        "1Y": (4.80, 2.50),
        "2Y": (5.00, 2.70),
    }

    base_spot = 7.2500

    # Generate ~400 days of data
    for days_ago in range(400):
        curve_date = _make_date(days_ago)
        # Simulate spot rate movement (small random walk)
        import random
        random.seed(days_ago)
        spot = base_spot + random.gauss(0, 0.02) * (400 - days_ago) / 400
        # Rates drift slowly
        drift = (400 - days_ago) / 400 * 0.5

        for tenor in tenors:
            foreign_rate, cny_rate = tenor_rates[tenor]
            records.append(
                FxImpliedRate(
                    curve_date=curve_date,
                    foreign_currency="USD",
                    tenor=tenor,
                    foreign_implied_rate=round(foreign_rate + drift, 4),
                    cny_risk_free_rate=round(cny_rate + drift * 0.5, 4),
                    spot_rate=round(spot, 4),
                    swap_points=None,
                    source="test_seed",
                )
            )

    session.add_all(records)
    session.commit()
    return records


# ============================================================================
# Resolve Params Endpoint
# ============================================================================


class TestResolveParamsEndpoint:
    """Tests for POST /api/v1/portfolios/{id}/resolve-params."""

    def test_resolve_returns_per_trade_params(
        self, client: TestClient, portfolio_with_trades: Portfolio,
        fx_implied_rate_data: list[FxImpliedRate],
    ):
        """Resolve endpoint should return params for each option trade."""
        pid = portfolio_with_trades.id
        resp = client.post(
            f"/api/v1/portfolios/{pid}/resolve-params",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["curve_type"] == "fx_implied_rate"
        assert len(data["trades"]) == 3  # all 3 trades returned

        # Trade 1: USD/CNY, 180 days → should have curve_resolved=true
        t1 = data["trades"][0]
        assert t1["ccy_pair"] == "USD/CNY"
        assert t1["curve_resolved"] is True
        assert t1["rf_rate_base"] is not None
        assert t1["rf_rate_quote"] is not None
        assert t1["spot"] is not None
        assert t1["volatility"] is not None
        assert t1["curve_date"] is not None

        # Trade 2: USD/CNY, 365 days → should have curve_resolved=true
        t2 = data["trades"][1]
        assert t2["curve_resolved"] is True

        # Trade 3: EUR/USD → quote not CNY → curve_resolved=false
        t3 = data["trades"][2]
        assert t3["ccy_pair"] == "EUR/USD"
        assert t3["curve_resolved"] is False
        assert t3["rf_rate_base"] is None
        assert t3["rf_rate_quote"] is None

    def test_different_maturities_produce_different_rates(
        self, client: TestClient, portfolio_with_trades: Portfolio,
        fx_implied_rate_data: list[FxImpliedRate],
    ):
        """Option trades with different expiries should get different interpolated rates."""
        pid = portfolio_with_trades.id
        resp = client.post(
            f"/api/v1/portfolios/{pid}/resolve-params",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 200
        trades = resp.json()["trades"]

        # Trade 1: ~6M maturity → rate should be near the 6M tenor
        t1 = trades[0]
        # Trade 2: ~12M maturity → rate should be near the 1Y tenor
        t2 = trades[1]

        # Both should have different rates (since maturities differ)
        assert t1["rf_rate_base"] != t2["rf_rate_base"], (
            f"Expected different rates for 6M vs 1Y maturities, "
            f"got {t1['rf_rate_base']} vs {t2['rf_rate_base']}"
        )

    def test_resolve_no_curve_data(
        self, client: TestClient, portfolio_with_trades: Portfolio,
    ):
        """When no FxImpliedRate data exists, params display empty (all None)."""
        pid = portfolio_with_trades.id
        resp = client.post(
            f"/api/v1/portfolios/{pid}/resolve-params",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 200
        trades = resp.json()["trades"]
        # No curve data → every field the curve would populate is empty
        for t in trades:
            assert t["rf_rate_base"] is None
            assert t["rf_rate_quote"] is None
            assert t["spot"] is None
            assert t["volatility"] is None
            assert t["curve_resolved"] is False
            assert t["curve_date"] is None

    def test_resolve_nonexistent_portfolio(self, client: TestClient):
        """404 for non-existent portfolio."""
        resp = client.post(
            "/api/v1/portfolios/99999/resolve-params",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 404

    def test_resolve_excludes_expired_options(
        self, client: TestClient, session: Session,
    ):
        """Expired options (expiry_date <= valuation_date) must not be returned."""
        portfolio = Portfolio(name="Expired Test", description="expiry filter")
        session.add(portfolio)
        session.flush()

        alive = OptionTrade(
            trade_id="ALIVE-001",
            portfolio_id=portfolio.id,
            ccy_pair="USD/CNY",
            trade_type="CALL",
            direction="买入",
            strike=7.1200,
            notional1=1_000_000.0,
            expiry_date=_future_date(90),
        )
        expired = OptionTrade(
            trade_id="EXPIRED-001",
            portfolio_id=portfolio.id,
            ccy_pair="USD/CNY",
            trade_type="PUT",
            direction="卖出",
            strike=7.0000,
            notional1=1_000_000.0,
            expiry_date=_make_date(30),  # 30 days ago → expired
        )
        session.add_all([alive, expired])
        session.commit()
        session.refresh(portfolio)

        resp = client.post(
            f"/api/v1/portfolios/{portfolio.id}/resolve-params",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
            },
        )
        assert resp.status_code == 200
        trades = resp.json()["trades"]
        trade_ids = [t["trade_id_str"] for t in trades]
        assert "ALIVE-001" in trade_ids
        assert "EXPIRED-001" not in trade_ids


# ============================================================================
# Greeks Calculation with Curve
# ============================================================================


class TestGreeksWithCurve:
    """Tests for POST /api/v1/portfolios/{id}/greeks with curve_type."""

    def test_greeks_with_curve_type_succeeds(
        self, client: TestClient, portfolio_with_trades: Portfolio,
        fx_implied_rate_data: list[FxImpliedRate],
    ):
        """Greeks calculation with curve_type should succeed."""
        pid = portfolio_with_trades.id
        resp = client.post(
            f"/api/v1/portfolios/{pid}/greeks",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
                "trade_params": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_id"] == pid
        assert data["trade_count"] == 3
        assert data["curve_type"] == "fx_implied_rate"
        assert len(data["trades"]) > 0

        # Results should be valid (no all-None)
        for t in data["trades"]:
            if not t.get("error"):
                assert t["delta"] is not None or t["error"] is not None

    def test_greeks_without_curve_type_errors_on_missing_params(
        self, client: TestClient, portfolio_with_trades: Portfolio,
    ):
        """Without curve_type or overrides, every live trade errors — no
        silent trade-default / hardcoded-default fallback."""
        pid = portfolio_with_trades.id
        resp = client.post(
            f"/api/v1/portfolios/{pid}/greeks",
            json={
                "valuation_date": _make_date(0).isoformat(),
                # no curve_type
                "trade_params": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["curve_type"] is None
        assert data["curve_valuation_date"] is None
        # No curve + no overrides + no defaults → every live trade errors
        for t in data["trades"]:
            assert t["error"] is not None

    def test_greeks_with_trade_params_override(
        self, client: TestClient, portfolio_with_trades: Portfolio,
        fx_implied_rate_data: list[FxImpliedRate],
    ):
        """User overrides in trade_params take priority."""
        pid = portfolio_with_trades.id
        resp = client.post(
            f"/api/v1/portfolios/{pid}/greeks",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
                "trade_params": [
                    {
                        "trade_id": portfolio_with_trades.option_trades[0].id,
                        "rf_rate_base": 0.055,   # explicit override
                        "rf_rate_quote": None,
                        "spot": 7.5000,
                        "volatility": None,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) >= 1
        # The first trade should have completed (no error)
        t1 = data["trades"][0]
        assert t1["error"] is None

    def test_greeks_with_trade_override_all_null(
        self, client: TestClient, portfolio_with_trades: Portfolio,
        fx_implied_rate_data: list[FxImpliedRate],
    ):
        """All-null overrides → curve resolution is used for CNY pairs."""
        pid = portfolio_with_trades.id
        trade_id_cny = portfolio_with_trades.option_trades[0].id  # USD/CNY
        resp = client.post(
            f"/api/v1/portfolios/{pid}/greeks",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "curve_type": "fx_implied_rate",
                "trade_params": [
                    {
                        "trade_id": trade_id_cny,
                        "rf_rate_base": None,
                        "rf_rate_quote": None,
                        "spot": None,
                        "volatility": None,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        # Should succeed — curve provides values
        data = resp.json()
        assert data["curve_type"] == "fx_implied_rate"

    def test_greeks_nonexistent_portfolio(self, client: TestClient):
        """404 for non-existent portfolio."""
        resp = client.post(
            "/api/v1/portfolios/99999/greeks",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "trade_params": [],
            },
        )
        assert resp.status_code == 404

    def test_empty_portfolio(self, client: TestClient, session: Session):
        """Portfolio with no option trades returns empty result."""
        portfolio = Portfolio(name="Empty Portfolio")
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)

        resp = client.post(
            f"/api/v1/portfolios/{portfolio.id}/greeks",
            json={
                "valuation_date": _make_date(0).isoformat(),
                "trade_params": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trade_count"] == 0
        assert len(data["trades"]) == 0
