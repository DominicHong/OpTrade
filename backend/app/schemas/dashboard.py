from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_trades: int = 0
    total_portfolios: int = 0
    total_counterparties: int = 0
    total_notional1: float = 0.0
    notional_by_ccy: dict[str, float] = {}
    trades_by_type: dict[str, int] = {}
    trades_by_status: dict[str, int] = {}


class RiskMetricsSummary(BaseModel):
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_vega: float = 0.0
    total_theta: float = 0.0
    total_rho: float = 0.0
    total_npv: float = 0.0
    trade_count_with_greeks: int = 0


class ExpiryProfile(BaseModel):
    bucket: str
    trade_count: int = 0
    total_notional: float = 0.0
    total_delta: float = 0.0
    total_gamma: float = 0.0


class CcyExposure(BaseModel):
    ccy_pair: str
    trade_count: int = 0
    total_notional: float = 0.0
    net_delta: float = 0.0
