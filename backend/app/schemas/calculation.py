from datetime import date, datetime

from pydantic import BaseModel


class GreeksResult(BaseModel):
    """Greeks calculation result for a single option trade."""

    trade_id: int
    calculation_date: date
    npv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None
    rho: float | None = None
    spot: float | None = None
    volatility: float | None = None
    rf_rate_base: float | None = None
    rf_rate_quote: float | None = None
    time_to_expiry_years: float | None = None
    scenario_label: str = "base"
    error: str | None = None

    model_config = {"from_attributes": True}


class GreeksRequest(BaseModel):
    """Request to calculate Greeks for one or more option trades."""

    trade_ids: list[int]
    spot: float | None = None
    volatility: float | None = None
    rf_rate_base: float | None = None
    rf_rate_quote: float | None = None
    valuation_date: date | None = None
    scenario_label: str = "base"


class PricingRequest(BaseModel):
    """Ad-hoc pricing request."""

    option_type: str
    direction: str
    spot: float
    strike: float
    volatility: float
    time_to_expiry_years: float
    rf_rate_base: float = 0.03
    rf_rate_quote: float = 0.03
    notional: float = 1.0


class PricingResult(BaseModel):
    npv: float | None = None
    fair_premium: float | None = None
    currency: str = "USD"
    error: str | None = None
