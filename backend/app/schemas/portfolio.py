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


class PortfolioGreeksRequest(BaseModel):
    """Request to calculate aggregated Greeks for a portfolio."""

    risk_free_rate: float = 0.03
    volatility: float | None = None
    spot: float | None = None
    valuation_date: date | None = None


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
    error: str | None = None


class PortfolioGreeksResponse(BaseModel):
    """Aggregated Greeks response for a portfolio."""

    portfolio_id: int
    portfolio_name: str
    trade_count: int
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_npv: float = 0.0
    risk_free_rate: float = 0.03
    volatility_used: float | None = None
    spot_used: float | None = None
    trades: list[TradeGreeksDetail] = []
