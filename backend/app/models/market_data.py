from __future__ import annotations

from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


class MarketDataSnapshot(SQLModel, table=True):
    __tablename__ = "market_data_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    ccy_pair: str = Field(max_length=20, index=True)
    spot: float | None = Field(default=None)
    volatility: float | None = Field(default=None)
    risk_free_rate_domestic: float | None = Field(default=None)
    risk_free_rate_foreign: float | None = Field(default=None)
    snapshot_date: date = Field(default_factory=date.today, index=True)
    source: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
