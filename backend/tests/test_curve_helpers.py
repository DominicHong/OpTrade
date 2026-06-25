"""
Unit tests for curve_helpers — pure functions with no DB dependencies.
"""

import math

import pytest

from app.utils.curve_helpers import (
    tenor_to_years,
    interpolate_rate,
    calc_historical_volatility,
    extract_foreign_currency,
)


# ============================================================================
# tenor_to_years
# ============================================================================


class TestTenorToYears:
    def test_1d(self):
        assert round(tenor_to_years("1D"), 8) == round(1.0 / 365, 8)

    def test_2d(self):
        assert round(tenor_to_years("2D"), 8) == round(2.0 / 365, 8)

    def test_1w(self):
        assert round(tenor_to_years("1W"), 8) == round(7.0 / 365, 8)

    def test_2w(self):
        assert round(tenor_to_years("2W"), 8) == round(14.0 / 365, 8)

    def test_1m(self):
        assert round(tenor_to_years("1M"), 8) == round(30.0 / 365, 8)

    def test_3m(self):
        assert round(tenor_to_years("3M"), 8) == round(90.0 / 365, 8)

    def test_6m(self):
        assert round(tenor_to_years("6M"), 8) == round(180.0 / 365, 8)

    def test_1y(self):
        assert tenor_to_years("1Y") == 1.0

    def test_2y(self):
        assert tenor_to_years("2Y") == 2.0

    def test_3y(self):
        assert tenor_to_years("3Y") == 3.0

    def test_lowercase(self):
        assert round(tenor_to_years("1m"), 8) == round(30.0 / 365, 8)

    def test_stripped(self):
        assert round(tenor_to_years(" 1D "), 8) == round(1.0 / 365, 8)

    def test_invalid_unit(self):
        with pytest.raises(ValueError):
            tenor_to_years("1X")

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            tenor_to_years("ABC")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            tenor_to_years("")


# ============================================================================
# interpolate_rate
# ============================================================================


class TestInterpolateRate:
    def test_exact_match(self):
        """Exact tenor match returns the exact rate."""
        result = interpolate_rate(
            0.25,
            tenors=["1M", "3M", "6M", "1Y"],
            rates=[4.0, 4.2, 4.5, 5.0],
        )
        assert result is not None
        # 3M = 90/365 ≈ 0.2466, which is very close to 0.25
        assert abs(result - 4.2) < 0.05

    def test_between_tenors(self):
        """Linear interpolation between two surrounding tenors."""
        result = interpolate_rate(
            0.5,
            tenors=["3M", "1Y"],
            rates=[4.0, 5.0],
        )
        assert result is not None
        # 3M = 0.0822, 1Y = 1.0. 0.5 is about halfway.
        t_3m = 90.0 / 365  # ≈ 0.2466
        t_1y = 1.0
        frac = (0.5 - t_3m) / (t_1y - t_3m)
        expected = 4.0 + frac * (5.0 - 4.0)
        assert abs(result - expected) < 0.01

    def test_below_min_flat(self):
        """Below first tenor → flat extrapolation."""
        result = interpolate_rate(
            0.001,  # ~0.37 days, well below 1D
            tenors=["1D", "1M", "1Y"],
            rates=[2.0, 3.0, 4.0],
        )
        assert result == 2.0

    def test_above_max_flat(self):
        """Above last tenor → flat extrapolation."""
        result = interpolate_rate(
            5.0,  # well beyond 3Y
            tenors=["6M", "1Y", "3Y"],
            rates=[3.0, 4.0, 5.0],
        )
        assert result == 5.0

    def test_single_point(self):
        """Only one valid data point → return that point."""
        result = interpolate_rate(
            0.5,
            tenors=["1Y"],
            rates=[4.5],
        )
        assert result == 4.5

    def test_all_none(self):
        """All rates are None → return None."""
        result = interpolate_rate(
            0.5,
            tenors=["1M", "3M", "1Y"],
            rates=[None, None, None],
        )
        assert result is None

    def test_mixed_none(self):
        """Some rates None → skip them, interpolate from valid ones."""
        result = interpolate_rate(
            0.5,
            tenors=["1M", "3M", "6M", "1Y"],
            rates=[None, 4.0, None, 5.0],
        )
        assert result is not None
        # Should interpolate between 3M (0.2466, 4.0) and 1Y (1.0, 5.0)
        t_3m = 90.0 / 365
        t_1y = 1.0
        frac = (0.5 - t_3m) / (t_1y - t_3m)
        expected = 4.0 + frac * (5.0 - 4.0)
        assert abs(result - expected) < 0.01

    def test_no_valid_tenor(self):
        """Invalid tenor strings are skipped; returns None if all skipped."""
        result = interpolate_rate(
            0.5,
            tenors=["XX", "YY"],
            rates=[4.0, 5.0],
        )
        assert result is None

    def test_unsorted_tenors(self):
        """Tenors provided in unsorted order still interpolate correctly."""
        result = interpolate_rate(
            0.5,
            tenors=["1Y", "1M", "6M", "3M"],
            rates=[5.0, 2.0, 4.5, 3.5],
        )
        assert result is not None
        # Should interpolate correctly between the sorted tenors
        assert 3.5 < result < 5.0


# ============================================================================
# calc_historical_volatility
# ============================================================================


class TestCalcHistoricalVol:
    def test_insufficient_data(self):
        """Fewer than 2 points → None."""
        assert calc_historical_volatility([]) is None
        assert calc_historical_volatility([7.0]) is None

    def test_two_points_insufficient(self):
        """Two points → only 1 log return → insufficient → None."""
        vol = calc_historical_volatility([7.0, 7.014])
        assert vol is None

    def test_three_points_valid(self):
        """Three points → 2 log returns → valid volatility."""
        vol = calc_historical_volatility([7.0, 7.014, 7.021])
        assert vol is not None
        assert vol > 0

    def test_constant_spot(self):
        """All spot rates identical → log returns are 0 → vol ≈ 0 → None."""
        vol = calc_historical_volatility([7.0, 7.0, 7.0, 7.0, 7.0])
        assert vol is None  # stddev of all-zeros → 0, annualised → 0, filtered out

    def test_known_volatility(self):
        """Verify against a hand-computed case."""
        # Daily log returns: ln(7.014/7.0) ≈ 0.001998
        #              ln(7.007/7.014) ≈ -0.000998
        #              ln(7.021/7.007) ≈ 0.001996
        rates = [7.0, 7.014, 7.007, 7.021]
        vol = calc_historical_volatility(rates)
        assert vol is not None

        log_ret = [
            math.log(7.014 / 7.0),
            math.log(7.007 / 7.014),
            math.log(7.021 / 7.007),
        ]
        mean_ret = sum(log_ret) / 3
        var = sum((r - mean_ret) ** 2 for r in log_ret) / 2  # ddof=1
        expected = math.sqrt(var) * math.sqrt(252)
        assert abs(vol - expected) < 1e-8

    def test_negative_spot_skipped(self):
        """Negative spot rates → log return skipped → insufficient data → None."""
        vol = calc_historical_volatility([7.0, -1.0, 7.014])
        # -1.0 blocks all log returns involving it → 0 valid returns → None
        assert vol is None

    def test_zero_spot_skipped(self):
        """Zero spot rate → log return skipped → insufficient data → None."""
        vol = calc_historical_volatility([7.0, 0.0, 7.014, 7.021])
        # 0.0 blocks returns involving it → only ln(7.021/7.014)=1 return → None
        assert vol is None

    def test_typical_fx_data(self):
        """A realistic 20-point FX series should produce reasonable vol."""
        import random
        random.seed(42)
        spot = 7.0
        rates = [spot]
        for _ in range(19):
            # Daily return ~0.0005 with σ~0.005
            ret = random.gauss(0.0002, 0.005)
            spot *= (1.0 + ret)
            rates.append(spot)
        vol = calc_historical_volatility(rates)
        assert vol is not None
        # Should be a reasonable annualized vol (maybe 5-15%)
        assert 0.01 < vol < 0.50


# ============================================================================
# extract_foreign_currency
# ============================================================================


class TestExtractForeignCurrency:
    def test_usd_cny(self):
        assert extract_foreign_currency("USD/CNY") == "USD"

    def test_eur_cny(self):
        assert extract_foreign_currency("EUR/CNY") == "EUR"

    def test_gbp_cny(self):
        assert extract_foreign_currency("GBP/CNY") == "GBP"

    def test_jpy_cny(self):
        assert extract_foreign_currency("JPY/CNY") == "JPY"

    def test_hkd_cny(self):
        assert extract_foreign_currency("HKD/CNY") == "HKD"

    def test_lowercase(self):
        assert extract_foreign_currency("usd/cny") == "USD"

    def test_spaces(self):
        assert extract_foreign_currency(" USD/CNY ") == "USD"

    def test_non_cny_quote_returns_none(self):
        """EUR/USD → quote is USD, not CNY → return None."""
        assert extract_foreign_currency("EUR/USD") is None

    def test_usd_jpy_returns_none(self):
        assert extract_foreign_currency("USD/JPY") is None

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            extract_foreign_currency("USDCNY")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            extract_foreign_currency("")

    def test_single_slash_raises(self):
        with pytest.raises(ValueError):
            extract_foreign_currency("/")

    def test_triple_slash_raises(self):
        with pytest.raises(ValueError):
            extract_foreign_currency("USD/CNY/EXTRA")
