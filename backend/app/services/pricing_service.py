"""
Pricing Service — QuantLib-based option pricing for FX options.

Supports vanilla European, barrier, and Asian options.
All QuantLib code is isolated in this service for testability.
"""

import QuantLib as ql
from app.utils.quantlib_helpers import get_ql_option_type, get_ql_position


class PricingService:
    """Option pricing using QuantLib."""

    def price_vanilla(
        self,
        option_type: str,
        direction: str,
        spot: float,
        strike: float,
        volatility: float,
        time_to_expiry_years: float,
        risk_free_rate_domestic: float = 0.03,
        risk_free_rate_foreign: float = 0.03,
        notional: float = 1.0,
    ) -> dict:
        """
        Price a plain vanilla European FX option.

        Returns:
            dict with: npv, fair_premium, currency, error
        """
        try:
            today = ql.Date.todaysDate()
            ql.Settings.instance().evaluationDate = today

            days_to_expiry = int(time_to_expiry_years * 365)
            expiry_date = today + days_to_expiry

            option_type_ql = get_ql_option_type(option_type)
            payoff = ql.PlainVanillaPayoff(option_type_ql, strike)
            exercise = ql.EuropeanExercise(expiry_date)

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

            bsm_process = ql.BlackScholesMertonProcess(
                spot_handle, r_for_handle, r_dom_handle, vol_handle
            )

            option = ql.VanillaOption(payoff, exercise)
            option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))

            npv = option.NPV() * notional

            # Adjust for position
            position = get_ql_position(direction)
            if position == ql.Position.Short:
                npv = -npv

            return {
                "npv": round(npv, 4),
                "fair_premium": round(abs(npv), 4),
                "currency": "base",
                "error": None,
            }

        except Exception as e:
            return {"npv": None, "fair_premium": None, "currency": "base", "error": str(e)}


# Singleton
pricing_service = PricingService()
