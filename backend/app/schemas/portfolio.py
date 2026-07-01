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
    """Request to resolve curve parameters for all option trades in a portfolio."""

    valuation_date: date
    curve_type: str = "fx_implied_rate"


class OptionTradeParamsResolved(BaseModel):
    """Per-option-trade resolved parameters from curve data."""

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
    """Response with per-option-trade resolved curve parameters."""

    valuation_date: date
    curve_type: str
    trades: list[OptionTradeParamsResolved]


# ---------------------------------------------------------------------------
# Per-trade parameter overrides (for the greeks endpoint)
# ---------------------------------------------------------------------------


class OptionTradeParamsOverride(BaseModel):
    """User-supplied overrides for a single option trade's valuation parameters.

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
    trade_params: list[OptionTradeParamsOverride] = []


class OptionTradeGreeksDetail(BaseModel):
    """Greeks result for a single option trade within a portfolio."""

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
    profit: float | None = None  # Buy: npv*notional - premium; Sell: premium + npv*notional
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
    trades: list[OptionTradeGreeksDetail] = []


# ---------------------------------------------------------------------------
# Multi-portfolio aggregated P&L analysis
# ---------------------------------------------------------------------------

SUPPORTED_CCY_PAIRS: set[str] = {"USD/CNY", "EUR/CNY", "HKD/CNY", "GBP/CNY", "JPY/CNY"}


class AggregatedAnalysisRequest(BaseModel):
    """Request for multi-portfolio aggregated P&L analysis."""

    portfolio_ids: list[int]
    start_date: date | None = None
    valuation_date: date
    curve_type: str | None = None
    trade_params: list[OptionTradeParamsOverride] = []


class AggregatedSummary(BaseModel):
    """Aggregated risk and P&L summary across portfolios."""

    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_npv: float = 0.0
    total_option_premium_pnl: float = 0.0
    total_option_exercise_pnl: float = 0.0
    total_option_pnl: float = 0.0
    total_spot_pnl: float = 0.0
    total_pnl: float = 0.0


class OptionTradeAnalysisDetail(BaseModel):
    """P&L detail for a single option trade in aggregated analysis."""

    trade_id: int
    trade_id_str: str | None = None
    ccy_pair: str | None = None
    option_type: str | None = None
    direction: str | None = None
    strike: float | None = None
    notional1: float | None = None
    trade_date: date | None = None
    expiry_date: date | None = None
    exercise_status: str | None = None
    delta: float | None = None
    gamma: float | None = None
    npv: float | None = None
    premium: float | None = None
    premium_pnl: float | None = None
    exercise_pnl: float | None = None
    total_pnl: float | None = None
    error: str | None = None


class SpotTradeAnalysisDetail(BaseModel):
    """P&L detail for a single spot trade in aggregated analysis."""

    trade_id: int
    trade_id_str: str | None = None
    ccy_pair: str | None = None
    direction: str | None = None
    deal_price: float | None = None
    market_rate: float | None = None
    adjusted_deal_price: float | None = None
    notional: float | None = None
    trade_date: date | None = None
    settlement_date: date | None = None
    pnl: float | None = None
    is_derivative: bool = False
    error: str | None = None


class AggregatedAnalysisResponse(BaseModel):
    """Response for multi-portfolio aggregated P&L analysis."""

    portfolio_name: str
    portfolio_count: int
    option_trade_count: int
    spot_trade_count: int
    start_date: date | None = None
    valuation_date: date | None = None
    curve_type: str | None = None
    curve_valuation_date: date | None = None
    summary: AggregatedSummary
    option_trades: list[OptionTradeAnalysisDetail] = []
    spot_trades: list[SpotTradeAnalysisDetail] = []
