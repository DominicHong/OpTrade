"""
Unit tests for GreeksService.

Tests vanilla option Greeks computation with known parameters.
All tests are pure unit tests — no database or HTTP required.
"""

import pytest

from app.services.greeks_service import GreeksService


@pytest.fixture
def svc():
    return GreeksService()


class TestVanillaGreeks:
    """Test vanilla European option Greeks."""

    def test_atm_call_greeks(self, svc):
        """ATM call option: delta should be ~0.5, gamma positive, vega positive."""
        result = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80,
            volatility=0.10, time_to_expiry_years=1.0,
        )
        assert result["error"] is None
        assert result["delta"] is not None
        assert 0.4 < result["delta"] < 0.7  # ATM call delta ≈ 0.5-0.6 for FX
        assert result["gamma"] > 0
        assert result["vega"] > 0
        assert result["npv"] > 0

    def test_deep_itm_call_delta(self, svc):
        """Deep in-the-money call: delta should be close to 1."""
        result = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=10.0, strike=6.80,
            volatility=0.10, time_to_expiry_years=1.0,
        )
        assert result["error"] is None
        assert result["delta"] is not None
        assert result["delta"] > 0.85  # deep ITM

    def test_otm_put_delta(self, svc):
        """OTM put: delta negative, close to 0."""
        result = svc.calculate_vanilla_greeks(
            option_type="Put", direction="Buy",
            spot=10.0, strike=6.80,
            volatility=0.10, time_to_expiry_years=1.0,
        )
        assert result["error"] is None
        assert result["delta"] is not None
        assert -0.15 < result["delta"] < 0  # far OTM put

    def test_short_position_signs(self, svc):
        """Short position: all signs should be flipped vs long."""
        long_result = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80,
            volatility=0.10, time_to_expiry_years=1.0,
        )
        short_result = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Sell",
            spot=6.80, strike=6.80,
            volatility=0.10, time_to_expiry_years=1.0,
        )
        assert long_result["error"] is None and short_result["error"] is None
        # Signs should be opposite
        assert abs(long_result["delta"] + short_result["delta"]) < 0.001

    def test_near_expiry_gamma(self, svc):
        """Near expiry: gamma should be larger than long-dated."""
        near = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80,
            volatility=0.10, time_to_expiry_years=0.01,
        )
        far = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80,
            volatility=0.10, time_to_expiry_years=1.0,
        )
        assert near["error"] is None and far["error"] is None
        assert near["gamma"] > far["gamma"]

    def test_higher_vol_increases_npv(self, svc):
        """Higher volatility → higher option NPV (vega positive)."""
        low_vol = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80,
            volatility=0.05, time_to_expiry_years=1.0,
        )
        high_vol = svc.calculate_vanilla_greeks(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80,
            volatility=0.20, time_to_expiry_years=1.0,
        )
        assert high_vol["npv"] > low_vol["npv"]
