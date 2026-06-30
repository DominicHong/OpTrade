from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class OptionTradeBase(BaseModel):
    """Common fields shared across option trade schemas."""

    # Polymorphic discriminator
    option_category: str = "fx_vanilla"

    # Core identifiers
    source_trade_id: str | None = None
    review_id: str | None = None
    leg: str | None = None
    portfolio_id: int | None = None
    counterparty_id: int | None = None
    portfolio_name: str | None = None
    counterparty_name: str | None = None

    # Option specs
    option_type: str | None = None
    trade_type: str | None = None
    direction: str | None = None
    strike: float | None = None
    ccy_pair: str | None = None
    trade_currency: str | None = None

    # Notional
    notional1: float | None = None
    notional2: float | None = None

    # Dates
    trade_date: date | None = None
    expiry_date: date | None = None
    delivery_date: date | None = None
    premium_payment_date: date | None = None

    # Premium
    premium_type: Literal["Pips", "%"] | None = None
    premium_rate: float | None = None
    premium_amount: float | None = None
    premium_currency: str | None = None

    # Market data
    spot_rate: float | None = None
    volatility: float | None = None

    # Status
    exercise_status: str | None = None
    delivery_status: str | None = None
    effective_status: str | None = None
    allocation_status: str | None = None

    # Venue
    venue: str | None = None
    clearing_method: str | None = None

    # Meta
    tenor: str | None = None
    event_type: str | None = None
    trade_purpose: str | None = None
    operator: str | None = None
    source: str | None = None
    comments: str | None = None

    @field_validator("premium_currency")
    @classmethod
    def validate_premium_currency(cls, v: str | None, info) -> str | None:
        if v is None:
            return v
        ccy_pair = info.data.get("ccy_pair")
        if ccy_pair:
            parts = ccy_pair.split("/")
            if len(parts) == 2 and v not in parts:
                raise ValueError("premium_currency must be one of the currencies in ccy_pair")
        return v


class OptionTradeRead(OptionTradeBase):
    """Schema for reading an OptionTrade (API response)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OptionTradeCreate(OptionTradeBase):
    """Schema for creating a new option trade manually."""

    trade_id: str


class OptionTradeUpdate(OptionTradeBase):
    """Fields that can be updated on an option trade."""

    trade_id: str | None = None


class OptionTradeListResponse(BaseModel):
    """Paginated list response for option trades."""

    data: list[OptionTradeRead]
    total: int
    page: int
    page_size: int


class OptionTradeFilterParams(BaseModel):
    """Query parameters for filtering option trades list."""

    page: int = 1
    page_size: int = 50
    sort_by: str = "trade_id"
    sort_order: str = "asc"  # asc or desc
    portfolio_id: int | None = None
    counterparty_id: int | None = None
    ccy_pair: str | None = None
    option_type: str | None = None
    trade_type: str | None = None
    direction: str | None = None
    expiry_from: date | None = None
    expiry_to: date | None = None
    trade_date_from: date | None = None
    trade_date_to: date | None = None
    search: str | None = None
    exercise_status: str | None = None
    option_category: str | None = None
