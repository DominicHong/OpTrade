from datetime import date, datetime

from pydantic import BaseModel


class PortfolioRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    trade_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str
    description: str | None = None


class PortfolioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class PortfolioGreeksSummary(BaseModel):
    portfolio_id: int
    portfolio_name: str
    trade_count: int
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_vega: float = 0.0
    total_theta: float = 0.0
    total_rho: float = 0.0
    total_npv: float = 0.0
    breakdown_by_ccy: dict[str, dict[str, float]] = {}


# ---------------------------------------------------------------------------
# Curve parameter resolution
# ---------------------------------------------------------------------------


class PortfolioResolveRequest(BaseModel):
    """Request to resolve curve parameters for all trades in a portfolio."""

    valuation_date: date
    curve_type: str = "fx_implied_rate"


class TradeParamsResolved(BaseModel):
    """Per-trade resolved parameters from curve data."""

    trade_id: int
    trade_id_str: str | None = None
    ccy_pair: str | None = None
    option_type: str | None = None
    direction: str | None = None
    strike: float | None = None
    notional1: float | None = None
    expiry_date: date | None = None
    remaining_maturity_years: float | None = None
    rf_rate_base: float | None = None  # decimal
    rf_rate_quote: float | None = None  # decimal
    spot: float | None = None
    volatility: float | None = None  # decimal, annualised
    curve_resolved: bool = False
    curve_date: date | None = None


class PortfolioResolveResponse(BaseModel):
    """Response with per-trade resolved curve parameters."""

    valuation_date: date
    curve_type: str
    trades: list[TradeParamsResolved]


# ---------------------------------------------------------------------------
# Per-trade parameter overrides (for the greeks endpoint)
# ---------------------------------------------------------------------------


class TradeParamsOverride(BaseModel):
    """User-supplied overrides for a single trade's valuation parameters.

    ``None`` means "resolve from curve (if available) or use trade default".
    """

    trade_id: int
    rf_rate_base: float | None = None
    rf_rate_quote: float | None = None
    spot: float | None = None
    volatility: float | None = None


# ---------------------------------------------------------------------------
# Greeks request / response
# ---------------------------------------------------------------------------


class PortfolioGreeksRequest(BaseModel):
    """Request to calculate aggregated Greeks for a portfolio."""

    valuation_date: date | None = None
    curve_type: str | None = None
    trade_params: list[TradeParamsOverride] = []


class TradeGreeksDetail(BaseModel):
    """Greeks result for a single trade within a portfolio."""

    trade_id: int
    trade_id_str: str | None = None
    ccy_pair: str | None = None
    option_type: str | None = None
    direction: str | None = None
    strike: float | None = None
    notional1: float | None = None
    delta: float | None = None
    gamma: float | None = None
    npv: float | None = None
    premium: float | None = None  # option premium, converted to ccy2
    profit: float | None = None  # Buy: npv*notional - premium; Sell: premium + npv*notional (QuantLib's option NPV is Negative for short)
    error: str | None = None


class PortfolioGreeksResponse(BaseModel):
    """Aggregated Greeks response for a portfolio."""

    portfolio_id: int
    portfolio_name: str
    trade_count: int
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_npv: float = 0.0
    total_profit: float = 0.0
    rf_rate_base: float | None = None
    rf_rate_quote: float | None = None
    volatility_used: float | None = None
    spot_used: float | None = None
    curve_type: str | None = None
    curve_valuation_date: date | None = None
    trades: list[TradeGreeksDetail] = []
