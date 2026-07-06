from datetime import date

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    option_trade_count: int = 0
    spot_trade_count: int = 0
    swap_trade_count: int = 0
    total_portfolios: int = 0
    total_counterparties: int = 0


class DashboardAnalysisRequest(BaseModel):
    start_date: date | None = None
    valuation_date: date
    curve_type: str | None = None


class DashboardDefaultsResponse(BaseModel):
    earliest_trade_date: str | None = None
    curve_type: str | None = None
