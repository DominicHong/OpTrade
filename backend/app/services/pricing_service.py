"""
Pricing Service — QuantLib-based option pricing for FX options.

Supports vanilla European, barrier, and Asian options.
All QuantLib code is isolated in this service for testability.
"""

import QuantLib as ql
from app.utils.quantlib_helpers import build_vanilla_option, get_ql_position


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
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        notional: float = 1.0,
    ) -> dict:
        """
        Price a plain vanilla European FX option.

        Returns:
            dict with: npv, fair_premium, currency, error
        """
        try:
            today = ql.Date.todaysDate()
            days_to_expiry = int(time_to_expiry_years * 365)
            expiry_date = today + days_to_expiry

            option = build_vanilla_option(
                option_type, strike, expiry_date, today,
                spot, volatility, rf_rate_base, rf_rate_quote,
            )

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
