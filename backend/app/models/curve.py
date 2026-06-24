"""Curve management models — registry + per-curve-type data tables.

This design allows adding new curve types (yield curves, vol surfaces, etc.)
by adding a new table + a row in curve_definitions, with no migration needed
for existing tables.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


class CurveDefinition(SQLModel, table=True):
    """Registry of available curve types and their data-source configuration."""

    __tablename__ = "curve_definitions"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, unique=True, index=True)
    curve_type: str = Field(max_length=50, index=True)
    description: str | None = Field(default=None, max_length=500)
    source_url: str | None = Field(default=None, max_length=500)
    parameters: str | None = Field(default=None)  # JSON string of crawl params
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FxImpliedRate(SQLModel, table=True):
    """FX implied rate curve data points.

    One row per (date, foreign_currency, tenor) triplet.
    Data source: chinamoney.com.cn 外币隐含利率曲线.

    Uniqueness of (date, foreign_currency, tenor) is enforced at the
    application layer via check-then-insert logic in the crawler / upload
    paths rather than via a DB-level UniqueConstraint.
    """

    __tablename__ = "fx_implied_rates"

    id: int | None = Field(default=None, primary_key=True)
    curve_date: date = Field(index=True)
    tenor: str = Field(max_length=20)  # "1D", "1W", "1M", "3M", "6M", "1Y", etc.
    foreign_currency: str = Field(max_length=10, index=True)  # "USD", "EUR", etc.

    # Core rate columns (matching chinamoney Excel export)
    foreign_implied_rate: float | None = Field(default=None)    # 隐含利率(%)
    cny_risk_free_rate: float | None = Field(default=None)      # 人民币利率(%)
    spot_rate: float | None = Field(default=None)               # 即期汇率
    swap_points: float | None = Field(default=None)             # 远/掉期点(Pips)

    # Metadata
    source: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
