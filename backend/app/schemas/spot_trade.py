from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SpotTradeBase(BaseModel):
    """Common fields shared across spot trade schemas."""

    trade_id: str | None = None
    portfolio_id: int | None = None
    counterparty_id: int | None = None
    portfolio_name: str | None = None
    counterparty_name: str | None = None

    # Trade details
    ccy_pair: str | None = None
    direction: str | None = None
    event_type: str | None = None

    deal_price: float | None = None
    ccy1_amount: float | None = None
    ccy2_amount: float | None = None
    ccy1: str | None = None
    ccy2: str | None = None

    # Dates
    trade_date: date | None = None
    settlement_date: date | None = None

    # Status and meta
    source: str | None = None
    venue: str | None = None


class SpotTradeRead(SpotTradeBase):
    """Schema for reading a SpotTrade (API response)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SpotTradeCreate(SpotTradeBase):
    """Schema for creating a new spot trade manually."""

    trade_id: str


class SpotTradeUpdate(SpotTradeBase):
    """Fields that can be updated on a spot trade."""

    pass


class SpotTradeListResponse(BaseModel):
    """Paginated list response for spot trades."""

    data: list[SpotTradeRead]
    total: int
    page: int
    page_size: int


class SpotTradeFilterParams(BaseModel):
    """Query parameters for filtering spot trades list."""

    page: int = 1
    page_size: int = 50
    sort_by: str = "trade_date"
    sort_order: str = "desc"
    portfolio_id: int | None = None
    counterparty_id: int | None = None
    ccy_pair: str | None = None
    direction: str | None = None
    event_type: str | None = None
    trade_date_from: date | None = None
    trade_date_to: date | None = None
    settlement_date_from: date | None = None
    settlement_date_to: date | None = None
    search: str | None = None
