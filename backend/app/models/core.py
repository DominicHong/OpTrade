"""
Core SQLModel entities: OptionTrade, Portfolio, Counterparty.

Consolidated into one file to avoid circular imports, since these models
cross-reference each other via SQLAlchemy relationships.

Option type extension pattern:
  OptionTrade (base table)          — common fields + "fx_vanilla" by default
  BarrierOptionDetails (child)       — barrier-specific fields, FK → option_trades.id
  AsianOptionDetails (child)         — asian/averaging-specific fields, FK → option_trades.id

Future option types (digital, compound, etc.) add new child tables with the same
one-to-one FK pattern.
"""

from datetime import date, datetime, timezone

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True, unique=True)
    description: str | None = Field(default=None, max_length=500)

    # One-to-many: Portfolio has many OptionTrades, SpotTrades and SwapTrades
    option_trades: list["OptionTrade"] = Relationship(back_populates="portfolio")
    spot_trades: list["SpotTrade"] = Relationship(back_populates="portfolio")
    swap_trades: list["SwapTrade"] = Relationship(back_populates="portfolio")


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparties"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=300, index=True, unique=True)
    short_name: str | None = Field(default=None, max_length=100)

    option_trades: list["OptionTrade"] = Relationship(back_populates="counterparty")
    spot_trades: list["SpotTrade"] = Relationship(back_populates="counterparty")
    swap_trades: list["SwapTrade"] = Relationship(back_populates="counterparty")


# ---------------------------------------------------------------------------
# Child detail tables (defined before OptionTrade to avoid forward-ref issues)
# ---------------------------------------------------------------------------


class BarrierOptionDetails(SQLModel, table=True):
    """Barrier-specific fields — one-to-one with OptionTrade."""

    __tablename__ = "barrier_option_details"

    id: int | None = Field(default=None, foreign_key="option_trades.id", primary_key=True)

    barrier_type: str | None = Field(default=None, max_length=50)
    barrier_direction: str | None = Field(default=None, max_length=20)
    barrier_level: float | None = Field(default=None)

    option_trade: "OptionTrade" = Relationship(back_populates="barrier_details")


class AsianOptionDetails(SQLModel, table=True):
    """Asian/averaging-specific fields — one-to-one with OptionTrade."""

    __tablename__ = "asian_option_details"

    id: int | None = Field(default=None, foreign_key="option_trades.id", primary_key=True)

    asian_sub_type: str | None = Field(default=None, max_length=50)
    averaging_method: str | None = Field(default=None, max_length=50)
    averaging_frequency: str | None = Field(default=None, max_length=50)
    averaging_rounding_method: str | None = Field(default=None, max_length=50)
    averaging_decimal_places: int | None = Field(default=None)
    reference_holiday: str | None = Field(default=None, max_length=100)
    observation_start_date: date | None = Field(default=None)
    observation_end_date: date | None = Field(default=None)
    averaging_start_date: date | None = Field(default=None)
    averaging_end_date: date | None = Field(default=None)

    option_trade: "OptionTrade" = Relationship(back_populates="asian_details")


# ---------------------------------------------------------------------------
# Base table
# ---------------------------------------------------------------------------


class OptionTrade(SQLModel, table=True):
    """Option trade entity mapping COMSTAR FX Options CSV export (~65 columns).

    FX vanilla options use this table directly (option_category="fx_vanilla").
    Barrier and Asian options add child detail tables via one-to-one FK.
    """

    __tablename__ = "option_trades"

    # === Option category discriminator ===
    option_category: str = Field(default="fx_vanilla", max_length=50)

    # === Primary Key & Core Identifiers ===
    id: int | None = Field(default=None, primary_key=True)
    trade_id: str = Field(max_length=200, index=True)
    source_trade_id: str | None = Field(default=None, max_length=200)
    review_id: str | None = Field(default=None, max_length=200)
    leg: str | None = Field(default=None, max_length=50)

    # === Foreign Keys ===
    portfolio_id: int | None = Field(default=None, foreign_key="portfolios.id", index=True)
    counterparty_id: int | None = Field(default=None, foreign_key="counterparties.id", index=True)

    # === Relationships ===
    portfolio: Portfolio | None = Relationship(back_populates="option_trades")
    counterparty: Counterparty | None = Relationship(back_populates="option_trades")
    barrier_details: BarrierOptionDetails | None = Relationship(back_populates="option_trade")
    asian_details: AsianOptionDetails | None = Relationship(back_populates="option_trade")

    # === Portfolio & Strategy ===
    portfolio_name: str | None = Field(default=None, max_length=200)
    allocation_status: str | None = Field(default=None, max_length=50)
    strategy_id: str | None = Field(default=None, max_length=200)
    strategy_trade_id: str | None = Field(default=None, max_length=200)
    is_selected: bool = False

    # === Option Specifications ===
    option_type: str | None = Field(default=None, max_length=50)
    trade_type: str | None = Field(default=None, max_length=20)
    direction: str | None = Field(default=None, max_length=20)
    strike: float | None = Field(default=None)
    ccy_pair: str | None = Field(default=None, max_length=20)
    trade_currency: str | None = Field(default=None, max_length=10)

    # === Notional ===
    notional1: float | None = Field(default=None)
    notional2: float | None = Field(default=None)
    ccy1: str | None = Field(default=None, max_length=10)
    ccy2: str | None = Field(default=None, max_length=10)

    # === Dates ===
    trade_date: date | None = Field(default=None)
    trade_time: str | None = Field(default=None, max_length=20)
    natural_date: date | None = Field(default=None)
    expiry_date: date | None = Field(default=None, index=True)
    delivery_date: date | None = Field(default=None)
    premium_payment_date: date | None = Field(default=None)

    # === Premium ===
    premium_type: str | None = Field(default=None, max_length=50)
    premium_rate: float | None = Field(default=None)
    premium_amount: float | None = Field(default=None)
    premium_currency: str | None = Field(default=None, max_length=10)
    cost_premium_rate: float | None = Field(default=None)
    cost_premium_amount: float | None = Field(default=None)

    # === Market Data (captured at trade time) ===
    spot_rate: float | None = Field(default=None)
    volatility: float | None = Field(default=None)
    volatility_reference: str | None = Field(default=None, max_length=100)

    # === Time / Schedule ===
    tenor: str | None = Field(default=None, max_length=50)
    timezone: str | None = Field(default=None, max_length=50)
    expiry_cutoff_time: str | None = Field(default=None, max_length=20)

    # === Return / Payoff ===
    return_amount: float | None = Field(default=None)
    return_currency: str | None = Field(default=None, max_length=10)

    # === Exercise ===
    exercise_status: str | None = Field(default=None, max_length=50)
    exercise_method: str | None = Field(default=None, max_length=50)
    exercise_trader: str | None = Field(default=None, max_length=100)
    exercise_time: str | None = Field(default=None, max_length=50)
    exercise_derivative_trade_id: str | None = Field(default=None, max_length=200)
    exercise_derivative_transaction_id: str | None = Field(default=None, max_length=200)
    exercise_derivative_product: str | None = Field(default=None, max_length=100)

    # === Delivery ===
    delivery_type: str | None = Field(default=None, max_length=50)
    delivery_currency: str | None = Field(default=None, max_length=10)
    delivery_reference_rate: float | None = Field(default=None)
    delivery_netting_rate: float | None = Field(default=None)

    # === Status Tracking ===
    effective_status: str | None = Field(default=None, max_length=50)

    # === Counterparty & Venue (denormalized for import) ===
    counterparty_name: str | None = Field(default=None, max_length=300)
    venue: str | None = Field(default=None, max_length=50)
    clearing_org: str | None = Field(default=None, max_length=100)
    clearing_method: str | None = Field(default=None, max_length=100)
    broker: str | None = Field(default=None, max_length=100)

    # === Trade Details ===
    event_type: str | None = Field(default=None, max_length=100)
    trade_purpose: str | None = Field(default=None, max_length=100)
    trade_nature: str | None = Field(default=None, max_length=50)
    operator: str | None = Field(default=None, max_length=100)
    our_side: str | None = Field(default=None, max_length=100)
    our_trader: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)
    client_profit: float | None = Field(default=None)

    # === Delta Exchange Fields ===
    delta_exchange_trade_id: str | None = Field(default=None, max_length=200)
    delta_exchange_transaction_id: str | None = Field(default=None, max_length=200)
    delta_exchange_product_type: str | None = Field(default=None, max_length=100)

    # === Flags ===
    is_related_party_trade: bool = False
    is_auto_exercise: bool = False
    has_original_trade: bool = False

    # === Comments & Meta ===
    comments: str | None = Field(default=None)
    event_comments: str | None = Field(default=None)
    operation_event: str | None = Field(default=None, max_length=100)

    # === Timestamps ===
    created_timestamp: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("premium_type")
    @classmethod
    def validate_premium_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Pips", "%"):
            raise ValueError("premium_type must be 'Pips' or '%'")
        return v

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


class SpotTrade(SQLModel, table=True):
    __tablename__ = "spot_trades"

    id: int | None = Field(default=None, primary_key=True)
    trade_id: str = Field(max_length=200, index=True)

    # Foreign Keys (reuse Portfolio, Counterparty)
    portfolio_id: int | None = Field(default=None, foreign_key="portfolios.id", index=True)
    counterparty_id: int | None = Field(default=None, foreign_key="counterparties.id", index=True)

    # Denormalized names for import convenience
    portfolio_name: str | None = Field(default=None, max_length=200)
    counterparty_name: str | None = Field(default=None, max_length=300)

    # Trade details
    ccy_pair: str | None = Field(default=None, max_length=20)
    direction: str | None = Field(default=None, max_length=20)
    event_type: str | None = Field(default=None, max_length=50)

    deal_price: float | None = Field(default=None)
    ccy1_amount: float | None = Field(default=None)
    ccy2_amount: float | None = Field(default=None)

    # Derived from ccy_pair on import
    ccy1: str | None = Field(default=None, max_length=10)
    ccy2: str | None = Field(default=None, max_length=10)

    # Dates
    trade_date: date | None = Field(default=None)
    settlement_date: date | None = Field(default=None)

    # Status and meta
    source: str | None = Field(default=None, max_length=100)
    venue: str | None = Field(default=None, max_length=50)
    created_timestamp: datetime | None = Field(default=None)

    # System timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    portfolio: Portfolio = Relationship(back_populates="spot_trades")
    counterparty: Counterparty = Relationship(back_populates="spot_trades")


class SwapTrade(SQLModel, table=True):
    """FX Swap trade entity mapping COMSTAR FX Swap Excel export.

    A swap has two legs: near (近端) and far (远端). P&L is realised from the
    price difference between the two legs in the quote currency (ccy2).
    """

    __tablename__ = "swap_trades"

    id: int | None = Field(default=None, primary_key=True)
    trade_id: str = Field(max_length=200, index=True)

    # Foreign Keys (reuse Portfolio, Counterparty)
    portfolio_id: int | None = Field(default=None, foreign_key="portfolios.id", index=True)
    counterparty_id: int | None = Field(default=None, foreign_key="counterparties.id", index=True)

    # Denormalized names for import convenience
    portfolio_name: str | None = Field(default=None, max_length=200)
    counterparty_name: str | None = Field(default=None, max_length=300)

    # Identifiers
    source_trade_id: str | None = Field(default=None, max_length=200)
    review_id: str | None = Field(default=None, max_length=200)

    # Trade details
    ccy_pair: str | None = Field(default=None, max_length=20)
    direction: str | None = Field(default=None, max_length=20)  # Buy/Sell | Sell/Buy
    swap_type: str | None = Field(default=None, max_length=50)  # 掉期类型
    event_type: str | None = Field(default=None, max_length=50)
    tenor: str | None = Field(default=None, max_length=50)
    spread: float | None = Field(default=None)  # 价差 (swap points)

    # Derived from ccy_pair on import
    ccy1: str | None = Field(default=None, max_length=10)
    ccy2: str | None = Field(default=None, max_length=10)

    # Spot reference (即期起息日 / 即期汇率)
    spot_value_date: date | None = Field(default=None)
    spot_rate: float | None = Field(default=None)

    # Near leg (近端)
    near_value_date: date | None = Field(default=None, index=True)
    near_tenor: str | None = Field(default=None, max_length=50)
    near_swap_points: float | None = Field(default=None)
    near_deal_price: float | None = Field(default=None)
    near_trade_ccy: str | None = Field(default=None, max_length=10)
    near_ccy1_amount: float | None = Field(default=None)
    near_ccy2_amount: float | None = Field(default=None)
    near_settlement_status: str | None = Field(default=None, max_length=50)

    # Far leg (远端)
    far_value_date: date | None = Field(default=None, index=True)
    far_tenor: str | None = Field(default=None, max_length=50)
    far_swap_points: float | None = Field(default=None)
    far_deal_price: float | None = Field(default=None)
    far_trade_ccy: str | None = Field(default=None, max_length=10)
    far_ccy1_amount: float | None = Field(default=None)
    far_ccy2_amount: float | None = Field(default=None)
    far_settlement_status: str | None = Field(default=None, max_length=50)

    # Dates
    trade_date: date | None = Field(default=None)
    trade_time: str | None = Field(default=None, max_length=20)
    natural_date: date | None = Field(default=None)

    # Counterparty & venue (denormalized for import)
    our_trader: str | None = Field(default=None, max_length=100)
    venue: str | None = Field(default=None, max_length=50)
    clearing_org: str | None = Field(default=None, max_length=100)
    clearing_method: str | None = Field(default=None, max_length=100)

    # Status and meta
    source: str | None = Field(default=None, max_length=100)
    comments: str | None = Field(default=None)
    created_timestamp: datetime | None = Field(default=None)

    # System timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    portfolio: Portfolio = Relationship(back_populates="swap_trades")
    counterparty: Counterparty = Relationship(back_populates="swap_trades")
