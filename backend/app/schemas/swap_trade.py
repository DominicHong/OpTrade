from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SwapTradeBase(BaseModel):
    """Common fields shared across swap trade schemas."""

    trade_id: str | None = None
    portfolio_id: int | None = None
    counterparty_id: int | None = None
    portfolio_name: str | None = None
    counterparty_name: str | None = None

    # Identifiers
    source_trade_id: str | None = None
    review_id: str | None = None

    # Trade details
    ccy_pair: str | None = None
    direction: str | None = None
    swap_type: str | None = None
    event_type: str | None = None
    tenor: str | None = None
    spread: float | None = None

    ccy1: str | None = None
    ccy2: str | None = None

    # Spot reference
    spot_value_date: date | None = None
    spot_rate: float | None = None

    # Near leg
    near_value_date: date | None = None
    near_tenor: str | None = None
    near_swap_points: float | None = None
    near_deal_price: float | None = None
    near_trade_ccy: str | None = None
    near_ccy1_amount: float | None = None
    near_ccy2_amount: float | None = None
    near_settlement_status: str | None = None

    # Far leg
    far_value_date: date | None = None
    far_tenor: str | None = None
    far_swap_points: float | None = None
    far_deal_price: float | None = None
    far_trade_ccy: str | None = None
    far_ccy1_amount: float | None = None
    far_ccy2_amount: float | None = None
    far_settlement_status: str | None = None

    # Dates
    trade_date: date | None = None
    trade_time: str | None = None
    natural_date: date | None = None

    # Status and meta
    our_trader: str | None = None
    venue: str | None = None
    clearing_org: str | None = None
    clearing_method: str | None = None
    source: str | None = None
    comments: str | None = None


class SwapTradeRead(SwapTradeBase):
    """Schema for reading a SwapTrade (API response)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SwapTradeCreate(SwapTradeBase):
    """Schema for creating a new swap trade manually."""

    trade_id: str


class SwapTradeUpdate(SwapTradeBase):
    """Fields that can be updated on a swap trade."""

    pass


class SwapTradeListResponse(BaseModel):
    """Paginated list response for swap trades."""

    data: list[SwapTradeRead]
    total: int
    page: int
    page_size: int


class SwapTradeFilterParams(BaseModel):
    """Query parameters for filtering swap trades list."""

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
    near_value_date_from: date | None = None
    near_value_date_to: date | None = None
    search: str | None = None
