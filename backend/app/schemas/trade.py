from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator


class TradeRead(BaseModel):
    """Schema for reading a Trade (API response)."""

    id: int
    trade_id: str
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
    premium_type: str | None = None
    premium_rate: float | None = None
    premium_amount: float | None = None
    premium_currency: str | None = None

    # Market data
    spot_rate: float | None = None
    volatility: float | None = None

    # Barrier
    barrier_type: str | None = None
    barrier_direction: str | None = None
    barrier_level: float | None = None

    # Asian
    asian_sub_type: str | None = None
    averaging_method: str | None = None

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

    # Timestamps
    trade_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TradeListResponse(BaseModel):
    """Paginated list response for trades."""

    data: list[TradeRead]
    total: int
    page: int
    page_size: int


class TradeCreate(BaseModel):
    """Schema for creating a new trade manually."""

    trade_id: str
    source_trade_id: str | None = None
    review_id: str | None = None
    leg: str | None = None
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

    # Barrier
    barrier_type: str | None = None
    barrier_direction: str | None = None
    barrier_level: float | None = None

    # Asian
    asian_sub_type: str | None = None
    averaging_method: str | None = None

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


class TradeUpdate(BaseModel):
    """Fields that can be updated on a trade."""

    trade_id: str | None = None
    source_trade_id: str | None = None
    review_id: str | None = None
    leg: str | None = None
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

    # Barrier
    barrier_type: str | None = None
    barrier_direction: str | None = None
    barrier_level: float | None = None

    # Asian
    asian_sub_type: str | None = None
    averaging_method: str | None = None

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


class TradeFilterParams(BaseModel):
    """Query parameters for filtering trades list."""

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
