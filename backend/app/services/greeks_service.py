"""
Greeks Service — QuantLib-based Greeks computation for FX options.

Computes Delta, Gamma, Vega, Theta, Rho, and NPV for vanilla options.
All QuantLib imports and calculations are confined to this service layer.
"""

from datetime import date

import QuantLib as ql
from app.utils.quantlib_helpers import get_ql_option_type, get_ql_position

# Fixed anchor date — avoids ql.Date.todaysDate() which makes results
# non-reproducible and dependent on the system clock.
_ANCHOR_DATE = ql.Date(15, 6, 2020)


class GreeksService:
    """Computes option Greeks using QuantLib's analytic engines."""

    def calculate_vanilla_greeks(
        self,
        option_type: str,
        direction: str,
        spot: float,
        strike: float,
        volatility: float,
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        valuation_date: date | None = None,
        expiry_date: date | None = None,
        time_to_expiry_years: float | None = None,
    ) -> dict:
        """
        Calculate Greeks for a plain vanilla European FX option.

        Time to expiry is specified via *valuation_date* and *expiry_date*
        (preferred — exact, reproducible). The legacy *time_to_expiry_years*
        is kept as a fallback for scenario analysis and only used when both
        dates are None.

        Args:
            option_type: "Call" or "Put"
            direction: "Buy" (Long) or "Sell" (Short)
            spot: Current spot price of the underlying
            strike: Strike price
            volatility: Implied volatility (decimal, e.g. 0.15 for 15%)
            rf_rate_base: Base currency risk-free rate (maps to QuantLib dividendYield)
            rf_rate_quote: Quote currency risk-free rate (maps to QuantLib riskFreeRate)
            valuation_date: Trade valuation date (preferred way to specify time)
            expiry_date: Option expiry date (preferred way to specify time)
            time_to_expiry_years: Time to expiry in years — only used when
                both valuation_date and expiry_date are None

        Returns:
            dict with keys: delta, gamma, vega, theta, rho, npv, error
        """
        try:
            # Determine evaluation/expiry dates and short-circuit expired
            # options in a single dispatch. Dates are preferred (exact,
            # reproducible); TTE is a fallback for scenario analysis.
            if valuation_date is not None and expiry_date is not None:
                # Same-day is still alive (option can be exercised on its
                # expiry date); strictly-after means expired → all Greeks 0.
                if valuation_date > expiry_date:
                    return {
                        "npv": 0.0,
                        "delta": 0.0,
                        "gamma": 0.0,
                        "vega": 0.0,
                        "theta": 0.0,
                        "rho": 0.0,
                        "error": None,
                    }
                # Exact dates — no precision loss, fully reproducible
                eval_d = ql.Date(
                    valuation_date.day, valuation_date.month, valuation_date.year
                )
                exp_d = ql.Date(
                    expiry_date.day, expiry_date.month, expiry_date.year
                )
            elif time_to_expiry_years is not None:
                if time_to_expiry_years <= 0:
                    return {
                        "npv": 0.0,
                        "delta": 0.0,
                        "gamma": 0.0,
                        "vega": 0.0,
                        "theta": 0.0,
                        "rho": 0.0,
                        "error": None,
                    }
                # Fallback: anchor + TTE (for scenario analysis).
                # Use int(x + 0.5) instead of int(x) to avoid FP truncation:
                # int(3/365*365) = int(2.999...) = 2 (WRONG, loses 33% of T)
                # int(3/365*365 + 0.5) = int(3.499...) = 3 (CORRECT)
                eval_d = _ANCHOR_DATE
                days = max(1, int(time_to_expiry_years * 365 + 0.5))
                exp_d = eval_d + days
            else:
                return {
                    "npv": 0.0,
                    "delta": 0.0,
                    "gamma": 0.0,
                    "vega": 0.0,
                    "theta": 0.0,
                    "rho": 0.0,
                    "error": "Either (valuation_date, expiry_date) or "
                             "time_to_expiry_years must be provided.",
                }

            ql.Settings.instance().evaluationDate = eval_d

            # Set up the option
            option_type_ql = get_ql_option_type(option_type)
            payoff = ql.PlainVanillaPayoff(option_type_ql, strike)
            exercise = ql.EuropeanExercise(exp_d)

            # Market data
            spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
            vol_handle = ql.BlackVolTermStructureHandle(
                ql.BlackConstantVol(eval_d, ql.TARGET(), volatility, ql.Actual365Fixed())
            )
            r_base_handle = ql.YieldTermStructureHandle(
                ql.FlatForward(eval_d, rf_rate_base, ql.Actual365Fixed())
            )
            r_quote_handle = ql.YieldTermStructureHandle(
                ql.FlatForward(eval_d, rf_rate_quote, ql.Actual365Fixed())
            )

            # Black-Scholes-Merton process for FX
            # r_base maps to dividendYield, r_quote maps to riskFreeRate
            bsm_process = ql.BlackScholesMertonProcess(
                spot_handle, r_base_handle, r_quote_handle, vol_handle
            )

            # Build option
            option = ql.VanillaOption(payoff, exercise)
            engine = ql.AnalyticEuropeanEngine(bsm_process)
            option.setPricingEngine(engine)

            # Read results
            npv = option.NPV()
            delta = option.delta()
            gamma = option.gamma()
            # Vega: sensitivity to 1% (0.01) vol change
            vega = option.vega() / 100.0
            # Theta: per-day theta (QuantLib returns per-year)
            theta = option.thetaPerDay()
            rho = option.rho() / 100.0  # per 1% rate change

            # Adjust for position direction (short position flips signs)
            position = get_ql_position(direction)
            if position == ql.Position.Short:
                npv = -npv
                delta = -delta
                gamma = -gamma
                vega = -vega
                theta = -theta
                rho = -rho

            return {
                "npv": round(npv, 6),
                "delta": round(delta, 6),
                "gamma": round(gamma, 6),
                "vega": round(vega, 6),
                "theta": round(theta, 6),
                "rho": round(rho, 6),
                "error": None,
            }

        except Exception as e:
            return {
                "npv": None,
                "delta": None,
                "gamma": None,
                "vega": None,
                "theta": None,
                "rho": None,
                "error": str(e),
            }

    def calculate_greeks_for_trade(
        self,
        spot: float,
        strike: float,
        volatility: float,
        time_to_expiry_years: float,
        option_type: str = "Call",
        direction: str = "Buy",
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        valuation_date: date | None = None,
        expiry_date: date | None = None,
    ) -> dict:
        """Convenience wrapper that matches the OptionTrade model's field names."""
        return self.calculate_vanilla_greeks(
            option_type=option_type,
            direction=direction,
            spot=spot,
            strike=strike,
            volatility=volatility,
            time_to_expiry_years=time_to_expiry_years,
            rf_rate_base=rf_rate_base,
            rf_rate_quote=rf_rate_quote,
            valuation_date=valuation_date,
            expiry_date=expiry_date,
        )


# Singleton
greeks_service = GreeksService()
