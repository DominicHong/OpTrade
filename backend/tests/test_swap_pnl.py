"""
Tests for FX Swap P&L algorithm in PortfolioService._process_swap_trade.

Covers buy/sell directions across the three lifecycle states (未起息 / 存续 / 到期),
the accrual pro-rating, and the annualised return-rate computation.
"""

from datetime import date

import pytest

from app.models import SwapTrade
from app.services.portfolio_service import PortfolioService


@pytest.fixture(name="service")
def service_fixture():
    # _process_swap_trade is pure (no session/db lookups) — bypass __init__
    return PortfolioService.__new__(PortfolioService)


def _make_swap(direction: str = "Buy/Sell") -> SwapTrade:
    """USD/JPY swap: near 161.6531, far 161.64, notional 10M USD.
    near_vd=2026-06-29, far_vd=2026-07-06 (7-day swap)."""
    return SwapTrade(
        id=1,
        trade_id="SW-1",
        ccy_pair="USD/JPY",
        direction=direction,
        near_deal_price=161.6531,
        far_deal_price=161.64,
        near_value_date=date(2026, 6, 29),
        far_value_date=date(2026, 7, 6),  # 7-day swap
        near_ccy1_amount=10_000_000.0,
        trade_date=date(2026, 6, 26),
    )


class TestSwapPnl:
    def test_buy_matured_full_pnl(self, service):
        t = _make_swap("Buy/Sell")
        d = service._process_swap_trade(t, date(2026, 7, 10))  # after far
        assert d.status == "到期"
        assert d.error is None
        # (far - near) * notional = (161.64 - 161.6531) * 10_000_000 = -131_000
        assert d.pnl == pytest.approx(-131_000.0, abs=0.01)

    def test_sell_matured_flipped_sign(self, service):
        t = _make_swap("Sell/Buy")
        d = service._process_swap_trade(t, date(2026, 7, 10))
        assert d.status == "到期"
        # sell: (near - far) * notional = +131_000
        assert d.pnl == pytest.approx(131_000.0, abs=0.01)

    def test_before_near_leg_zero_pnl(self, service):
        t = _make_swap("Buy/Sell")
        d = service._process_swap_trade(t, date(2026, 6, 28))
        assert d.status == "未起息"
        assert d.pnl == 0.0
        assert d.pnl == 0  # also guards against -0.0

    def test_accrual_pro_rata_mid_life(self, service):
        t = _make_swap("Buy/Sell")  # 7-day swap, full = -131_000
        # 3 days elapsed of 7 → -131_000 * 3/7
        d = service._process_swap_trade(t, date(2026, 7, 2))
        assert d.status == "存续"
        expected = -131_000.0 * 3 / 7
        assert d.pnl == pytest.approx(expected, abs=0.01)

    def test_accrual_at_near_leg_zero(self, service):
        t = _make_swap("Buy/Sell")
        d = service._process_swap_trade(t, date(2026, 6, 29))  # elapsed=0
        assert d.status == "存续"
        assert d.pnl == 0.0

    def test_accrual_at_far_leg_full(self, service):
        t = _make_swap("Buy/Sell")
        # exactly on far_value_date → considered matured (>= far)
        d = service._process_swap_trade(t, date(2026, 7, 6))
        assert d.status == "到期"
        assert d.pnl == pytest.approx(-131_000.0, abs=0.01)

    def test_return_rate_buy(self, service):
        t = _make_swap("Buy/Sell")
        d = service._process_swap_trade(t, date(2026, 7, 10))
        # (far-near)/near * 365/days * 100, 2 decimals
        expected = (161.64 - 161.6531) / 161.6531 * 365 / 7 * 100
        assert d.return_rate == pytest.approx(round(expected, 2), abs=0.01)

    def test_return_rate_sell_flipped(self, service):
        t = _make_swap("Sell/Buy")
        d = service._process_swap_trade(t, date(2026, 7, 10))
        expected = (161.6531 - 161.64) / 161.6531 * 365 / 7 * 100
        assert d.return_rate == pytest.approx(round(expected, 2), abs=0.01)
        assert d.return_rate > 0

    def test_missing_data_error(self, service):
        t = _make_swap("Buy/Sell")
        t.far_deal_price = None
        d = service._process_swap_trade(t, date(2026, 7, 10))
        assert d.error is not None
        assert d.pnl is None

    def test_missing_ccy_pair_error(self, service):
        t = _make_swap("Buy/Sell")
        t.ccy_pair = None
        d = service._process_swap_trade(t, date(2026, 7, 10))
        assert d.error == "Missing currency pair"

    def test_notional_uses_absolute_value(self, service):
        """Near-leg ccy1 amount is negative for a Sell/Buy — PnL must use |notional|."""
        t = _make_swap("Sell/Buy")
        t.near_ccy1_amount = -10_000_000.0  # signed as it comes from ComStar
        d = service._process_swap_trade(t, date(2026, 7, 10))
        assert d.pnl == pytest.approx(131_000.0, abs=0.01)
