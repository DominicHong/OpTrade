"""
Core SQLModel entities: Trade, Portfolio, Counterparty, CalculationResult.

Consolidated into one file to avoid circular imports, since these models
cross-reference each other via SQLAlchemy relationships.
"""

from datetime import date, datetime, timezone

from sqlmodel import Field, Relationship, SQLModel


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True, unique=True)
    description: str | None = Field(default=None, max_length=500)

    # One-to-many: Portfolio has many Trades
    trades: list["Trade"] = Relationship(back_populates="portfolio")


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparties"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=300, index=True, unique=True)
    short_name: str | None = Field(default=None, max_length=100)

    trades: list["Trade"] = Relationship(back_populates="counterparty")


class Trade(SQLModel, table=True):
    """Central trade entity mapping COMSTAR FX Options CSV export (~90 columns)."""

    __tablename__ = "trades"

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
    portfolio: Portfolio | None = Relationship(back_populates="trades")
    counterparty: Counterparty | None = Relationship(back_populates="trades")
    calculation_results: list["CalculationResult"] = Relationship(back_populates="trade")

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
    observation_start_date: date | None = Field(default=None)
    observation_end_date: date | None = Field(default=None)
    averaging_start_date: date | None = Field(default=None)
    averaging_end_date: date | None = Field(default=None)

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

    # === Barrier Option Fields ===
    barrier_type: str | None = Field(default=None, max_length=50)
    barrier_direction: str | None = Field(default=None, max_length=20)
    barrier_level: float | None = Field(default=None)

    # === Asian Option Fields ===
    asian_sub_type: str | None = Field(default=None, max_length=50)
    averaging_method: str | None = Field(default=None, max_length=50)
    averaging_frequency: str | None = Field(default=None, max_length=50)
    averaging_rounding_method: str | None = Field(default=None, max_length=50)
    averaging_decimal_places: int | None = Field(default=None)
    reference_holiday: str | None = Field(default=None, max_length=100)

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
    delivery_status: str | None = Field(default=None, max_length=50)
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


class CalculationResult(SQLModel, table=True):
    __tablename__ = "calculation_results"

    id: int | None = Field(default=None, primary_key=True)
    trade_id: int = Field(foreign_key="trades.id", index=True)

    calculation_date: date = Field(default_factory=date.today)
    spot: float | None = Field(default=None)
    volatility: float | None = Field(default=None)
    risk_free_rate: float | None = Field(default=None)
    time_to_expiry_years: float | None = Field(default=None)

    npv: float | None = Field(default=None)
    delta: float | None = Field(default=None)
    gamma: float | None = Field(default=None)
    vega: float | None = Field(default=None)
    theta: float | None = Field(default=None)
    rho: float | None = Field(default=None)

    scenario_label: str | None = Field(default=None, max_length=100, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    trade: Trade = Relationship(back_populates="calculation_results")
