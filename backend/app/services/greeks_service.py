"""
Greeks Service — QuantLib-based Greeks computation for FX options.

Computes Delta, Gamma, Vega, Theta, Rho, and NPV for vanilla options.
All QuantLib imports and calculations are confined to this service layer.
"""

from datetime import date

import QuantLib as ql
from app.utils.quantlib_helpers import get_ql_option_type, get_ql_position


class GreeksService:
    """Computes option Greeks using QuantLib's analytic engines."""

    def calculate_vanilla_greeks(
        self,
        option_type: str,
        direction: str,
        spot: float,
        strike: float,
        volatility: float,
        time_to_expiry_years: float,
        risk_free_rate_domestic: float = 0.03,
        risk_free_rate_foreign: float = 0.03,
    ) -> dict:
        """
        Calculate Greeks for a plain vanilla European FX option.

        Args:
            option_type: "Call" or "Put"
            direction: "Buy" (Long) or "Sell" (Short)
            spot: Current spot price of the underlying
            strike: Strike price
            volatility: Implied volatility (decimal, e.g. 0.15 for 15%)
            time_to_expiry_years: Time to expiry in years
            risk_free_rate_domestic: Domestic risk-free rate
            risk_free_rate_foreign: Foreign risk-free rate (for FX options)

        Returns:
            dict with keys: delta, gamma, vega, theta, rho, npv, error
        """
        try:
            today = ql.Date.todaysDate()
            ql.Settings.instance().evaluationDate = today

            # Calculate expiry date
            days_to_expiry = int(time_to_expiry_years * 365)
            expiry_date = today + days_to_expiry

            # Set up the option
            option_type_ql = get_ql_option_type(option_type)
            payoff = ql.PlainVanillaPayoff(option_type_ql, strike)
            exercise = ql.EuropeanExercise(expiry_date)

            # Market data
            spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
            vol_handle = ql.BlackVolTermStructureHandle(
                ql.BlackConstantVol(today, ql.TARGET(), volatility, ql.Actual365Fixed())
            )
            r_dom_handle = ql.YieldTermStructureHandle(
                ql.FlatForward(today, risk_free_rate_domestic, ql.Actual365Fixed())
            )
            r_for_handle = ql.YieldTermStructureHandle(
                ql.FlatForward(today, risk_free_rate_foreign, ql.Actual365Fixed())
            )

            # Black-Scholes-Merton process for FX
            bsm_process = ql.BlackScholesMertonProcess(
                spot_handle, r_for_handle, r_dom_handle, vol_handle
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
        risk_free_rate: float = 0.03,
    ) -> dict:
        """Convenience wrapper that matches the Trade model's field names."""
        return self.calculate_vanilla_greeks(
            option_type=option_type,
            direction=direction,
            spot=spot,
            strike=strike,
            volatility=volatility,
            time_to_expiry_years=time_to_expiry_years,
            risk_free_rate_domestic=risk_free_rate,
            risk_free_rate_foreign=risk_free_rate,
        )


# Singleton
greeks_service = GreeksService()
