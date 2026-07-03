"""Pydantic schemas for exchange rate management API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ExchangeRateRead(BaseModel):
    """Read model for a single exchange rate row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rate_date: date
    ccy_pair: str
    rate: float
    source: str
    source_ref: str | None = None
    created_at: datetime | None = None


class ExchangeRateFilterParams(BaseModel):
    """Query-string filter parameters for listing exchange rates."""

    date_from: date | None = None
    date_to: date | None = None
    ccy_pair: str | None = None
    source: str | None = None
    page: int = 1
    page_size: int = 100
    sort_by: str = "rate_date"
    sort_order: str = "desc"


class ExchangeRateListResponse(BaseModel):
    """Paginated response for exchange rate queries."""

    data: list[ExchangeRateRead]
    total: int
    page: int
    page_size: int


class ExchangeRateCoverageSummary(BaseModel):
    """High-level data coverage information for exchange rates."""

    total_records: int = 0
    date_from: date | None = None
    date_to: date | None = None
    ccy_pairs: list[str] = []
    last_updated: datetime | None = None


class ExchangeRateManualCreate(BaseModel):
    """Manual entry payload for a single exchange rate."""

    rate_date: date
    ccy_pair: str
    rate: float
    source: str = "manual"
    source_ref: str | None = None


class ExchangeRateImportResult(BaseModel):
    """Result of an import-from-curve or upload operation."""

    records_added: int = 0
    records_updated: int = 0
    skipped: int = 0
    message: str = ""


class ExchangeRateUploadResult(BaseModel):
    """Result of a manual XLSX/CSV upload."""

    records_added: int = 0
    records_updated: int = 0
    skipped: int = 0
    message: str = ""
