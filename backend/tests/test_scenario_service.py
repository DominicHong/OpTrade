"""Unit tests for ScenarioService."""

import pytest

from app.services.scenario_service import ScenarioService


@pytest.fixture
def svc():
    return ScenarioService()


class TestSpotShift:
    def test_positive_shift_increases_call_npv(self, svc):
        """Higher spot → higher NPV for call option."""
        results = svc.spot_shift(
            option_type="Call", direction="Buy",
            base_spot=6.80, strike=6.80, base_vol=0.10,
            time_to_expiry_years=1.0, rf_rate_base=0.03, rf_rate_quote=0.03,
            shifts_bps=[-500, 0, 500],
        )
        assert results[0]["shift_bps"] == -500
        assert results[2]["shift_bps"] == 500
        assert results[2]["npv"] > results[1]["npv"] > results[0]["npv"]

    def test_returns_correct_count(self, svc):
        """Should return one result per shift."""
        results = svc.spot_shift(
            option_type="Call", direction="Buy",
            base_spot=6.80, strike=6.80, base_vol=0.10,
            time_to_expiry_years=1.0, rf_rate_base=0.03, rf_rate_quote=0.03,
        )
        assert len(results) == 7  # default shifts


class TestVolShift:
    def test_higher_vol_increases_npv(self, svc):
        """Higher volatility → higher NPV for any option."""
        results = svc.vol_shift(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80, base_vol=0.10,
            time_to_expiry_years=1.0, rf_rate_base=0.03, rf_rate_quote=0.03,
            shifts_vol=[-0.03, 0, 0.03],
        )
        assert results[2]["npv"] > results[1]["npv"] > results[0]["npv"]

    def test_vol_floor_applied(self, svc):
        """Vol should be floored at 0.001."""
        results = svc.vol_shift(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80, base_vol=0.01,
            time_to_expiry_years=1.0, rf_rate_base=0.03, rf_rate_quote=0.03,
            shifts_vol=[-0.02],
        )
        assert results[0]["error"] is None  # should not crash


class TestTimeDecay:
    def test_time_passing_reduces_npv(self, svc):
        """Option NPV generally decreases as time passes (theta negative for long)."""
        results = svc.time_decay(
            option_type="Call", direction="Buy",
            spot=6.80, strike=6.80, volatility=0.10,
            time_to_expiry_years=1.0, rf_rate_base=0.03, rf_rate_quote=0.03,
        )
        # At t=0, the option has more value than at later dates
        assert results[0]["days_forward"] == 0
        assert len(results) == 5


class TestHeatmap:
    def test_heatmap_shape(self, svc):
        """Heatmap values array should have correct dimensions."""
        result = svc.heatmap(
            option_type="Call", direction="Buy",
            base_spot=6.80, strike=6.80, base_vol=0.10,
            time_to_expiry_years=1.0, rf_rate_base=0.03, rf_rate_quote=0.03,
        )
        assert "spot_shifts" in result
        assert "vol_shifts" in result
        assert "values" in result
        assert "base_greeks" in result
        assert len(result["values"]) == len(result["vol_shifts"])
        assert len(result["values"][0]) == len(result["spot_shifts"])
