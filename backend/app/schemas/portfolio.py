from datetime import date, datetime

from pydantic import BaseModel

from app.utils.currency_pairs import SUPPORTED_CCY_PAIRS


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

# SUPPORTED_CCY_PAIRS is re-exported from app.utils.currency_pairs (see top).


class AggregatedAnalysisRequest(BaseModel):
    """Request for multi-portfolio aggregated P&L analysis."""

    portfolio_ids: list[int]
    start_date: date | None = None
    valuation_date: date
    curve_type: str | None = None
    trade_params: list[OptionTradeParamsOverride] = []


class CcyPairOptionMetrics(BaseModel):
    """Option risk metrics for a single currency pair.

    P&L items are converted to CNY using the valuation-date exchange rate
    for the pair's quote currency (ccy2).  Greeks are in the original
    ``ccy2 / 1 ccy1`` unit so they remain applicable to the pair's notional.
    """

    ccy_pair: str
    # (a) CNY-converted P&L items
    npv_cny: float = 0.0
    premium_pnl_cny: float = 0.0       # 估值损益
    exercise_pnl_cny: float = 0.0      # 行权损益
    total_option_pnl_cny: float = 0.0  # 期权总损益
    # (b) Greeks in original currency
    delta: float = 0.0
    gamma: float = 0.0
    # Transparency: the FX rate used to convert ccy2 → CNY (1.0 if ccy2 == CNY)
    fx_rate_to_cny: float | None = None
    # Trade count for context
    trade_count: int = 0


class AggregatedSummary(BaseModel):
    """Aggregated risk and P&L summary across portfolios (multi-currency).

    All P&L amounts are denominated in CNY (converted via valuation-date
    exchange rates).  Delta / Gamma are kept per-currency-pair in the
    original quote currency (ccy2 / 1 ccy1) — they are NOT summed across
    pairs because that would be financially meaningless.
    """

    # (1) Option risk metrics — one entry per currency pair with trades
    option_metrics_by_ccy_pair: list[CcyPairOptionMetrics] = []
    # (2) Portfolio-level P&L (all CNY)
    total_option_pnl_cny: float = 0.0       # = Σ option_metrics.total_option_pnl_cny
    total_spot_pnl_cny: float = 0.0
    total_swap_pnl_cny: float = 0.0
    total_pnl_cny: float = 0.0              # = total_option_pnl_cny + total_spot_pnl_cny + total_swap_pnl_cny
    # (3) Spot currency exposures (raw, unchanged from prior implementation)
    currency_exposures: dict[str, float] = {}


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
    # CNY-converted mirror (for display/audit).  ``None`` when no FX rate available.
    premium_pnl_cny: float | None = None
    exercise_pnl_cny: float | None = None
    total_pnl_cny: float | None = None
    npv_cny: float | None = None
    fx_rate_to_cny: float | None = None
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
    # CNY-converted mirror (pnl is in ccy2; pnl_cny = pnl × fx_rate_to_cny)
    pnl_cny: float | None = None
    fx_rate_to_cny: float | None = None
    is_derivative: bool = False
    error: str | None = None


class SwapTradeAnalysisDetail(BaseModel):
    """P&L detail for a single swap trade in aggregated analysis.

    ``pnl`` is in the swap's quote currency (ccy2); ``pnl_cny`` is the
    CNY-converted mirror.  ``return_rate`` is the annualised return in
    percent (2 decimals).  ``status`` is one of: 未起息 / 存续 / 到期.
    """

    trade_id: int
    trade_id_str: str | None = None
    ccy_pair: str | None = None
    direction: str | None = None
    near_deal_price: float | None = None
    far_deal_price: float | None = None
    near_value_date: date | None = None
    far_value_date: date | None = None
    notional: float | None = None
    trade_date: date | None = None
    status: str | None = None
    pnl: float | None = None          # original currency (ccy2)
    pnl_cny: float | None = None
    return_rate: float | None = None  # annualised percent, 2 decimals
    fx_rate_to_cny: float | None = None
    error: str | None = None


class AggregatedAnalysisResponse(BaseModel):
    """Response for multi-portfolio aggregated P&L analysis."""

    portfolio_name: str
    portfolio_count: int
    option_trade_count: int
    spot_trade_count: int
    swap_trade_count: int = 0
    start_date: date | None = None
    valuation_date: date | None = None
    curve_type: str | None = None
    curve_valuation_date: date | None = None
    summary: AggregatedSummary
    option_trades: list[OptionTradeAnalysisDetail] = []
    spot_trades: list[SpotTradeAnalysisDetail] = []
    swap_trades: list[SwapTradeAnalysisDetail] = []
