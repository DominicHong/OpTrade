"""Exchange rate model — per (date, ccy_pair) spot rate for multi-currency P&L.

Distinct from ``FxImpliedRate`` (which is a curve: one row per
``(date, ccy, tenor)``).  ``ExchangeRate`` is the single spot rate used to
convert P&L from a trade's quote currency into CNY for aggregation.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.utils.date_utils import utc_now


class ExchangeRate(SQLModel, table=True):
    """Spot exchange rate for a currency pair on a given date.

    One row per ``(rate_date, ccy_pair)``.  Uniqueness is enforced at the
    application layer (upsert in ``ExchangeRateService``) to keep the
    SQLite schema simple.
    """

    __tablename__ = "exchange_rates"

    id: int | None = Field(default=None, primary_key=True)
    rate_date: date = Field(index=True)
    ccy_pair: str = Field(max_length=20, index=True)  # "USD/CNY", "EUR/USD", ...
    rate: float  # 1 unit ccy1 = `rate` units ccy2
    source: str = Field(max_length=50)  # "fx_implied_curve" | "cross_derived" | "manual" | "upload"
    source_ref: str | None = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=utc_now)
