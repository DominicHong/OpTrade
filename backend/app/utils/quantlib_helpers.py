"""
QuantLib helper utilities — date conversion, option type mapping, instrument builders.

All QuantLib imports are confined to this module and the services layer.
"""

from datetime import date

import QuantLib as ql


def date_to_ql(date_obj: date) -> "ql.Date":
    """Convert Python date to QuantLib Date."""

    return ql.Date(date_obj.day, date_obj.month, date_obj.year)


def ql_to_date(ql_date: "ql.Date") -> date:
    """Convert QuantLib Date to Python date."""

    return date(ql_date.year(), ql_date.month(), ql_date.dayOfMonth())


def get_ql_option_type(option_type: str) -> "ql.Option.Type":
    """Map 'Call'/'Put' string to QuantLib option type."""

    mapping = {
        "call": ql.Option.Call,
        "CALL": ql.Option.Call,
        "put": ql.Option.Put,
        "PUT": ql.Option.Put,
    }
    return mapping.get(option_type.lower(), ql.Option.Call)


def get_ql_position(direction: str) -> "ql.Position.Type":
    """Map 'Buy'/'Sell' string to QuantLib position type."""

    mapping = {
        "buy": ql.Position.Long,
        "BUY": ql.Position.Long,
        "买入": ql.Position.Long,
        "sell": ql.Position.Short,
        "SELL": ql.Position.Short,
        "卖出": ql.Position.Short,
    }
    return mapping.get(direction.lower(), ql.Position.Long)


def days_to_years(days: int) -> float:
    """Convert days to year fraction (Actual/365 convention)."""
    return days / 365.0


def get_valuation_date(today: date | None = None) -> "ql.Date":
    """Get QuantLib valuation date (today or a specified date)."""

    if today is None:
        today = date.today()
    return date_to_ql(today)


def build_vanilla_option(
    option_type: str,
    strike: float,
    expiry_date: "ql.Date",
    eval_date: "ql.Date",
    spot: float,
    volatility: float,
    rf_rate_base: float,
    rf_rate_quote: float,
) -> "ql.VanillaOption":
    """Build a priced vanilla European FX option (Black-Scholes-Merton).

    Sets the evaluation date, constructs payoff / exercise / market-data
    handles, attaches the ``AnalyticEuropeanEngine`` and returns the option
    ready for ``.NPV()`` / ``.delta()`` / ``.gamma()`` / ``.vega()`` /
    ``.thetaPerDay()`` / ``.rho()``.

    ``rf_rate_base`` maps to the dividend yield (base currency) and
    ``rf_rate_quote`` maps to the risk-free rate (quote currency).
    """
    ql.Settings.instance().evaluationDate = eval_date

    payoff = ql.PlainVanillaPayoff(get_ql_option_type(option_type), strike)
    exercise = ql.EuropeanExercise(expiry_date)

    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
    vol_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(eval_date, ql.TARGET(), volatility, ql.Actual365Fixed())
    )
    r_base_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(eval_date, rf_rate_base, ql.Actual365Fixed())
    )
    r_quote_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(eval_date, rf_rate_quote, ql.Actual365Fixed())
    )

    bsm_process = ql.BlackScholesMertonProcess(
        spot_handle, r_base_handle, r_quote_handle, vol_handle
    )

    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))
    return option
