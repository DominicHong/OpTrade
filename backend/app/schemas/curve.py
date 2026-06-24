"""Pydantic schemas for curve management API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Curve Definition
# ---------------------------------------------------------------------------


class CurveDefinitionRead(BaseModel):
    """Read model for a curve definition registry entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    curve_type: str
    description: str | None = None
    source_url: str | None = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# FX Implied Rate — Read
# ---------------------------------------------------------------------------


class FxImpliedRateRead(BaseModel):
    """Read model for a single FX implied rate data point."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    curve_date: date
    tenor: str
    foreign_currency: str
    foreign_implied_rate: float | None = None
    cny_risk_free_rate: float | None = None
    spot_rate: float | None = None
    swap_points: float | None = None
    source: str | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# FX Implied Rate — Filter & List
# ---------------------------------------------------------------------------


class FxImpliedRateFilterParams(BaseModel):
    """Query-string filter parameters for listing FX implied rates."""

    date_from: date | None = None
    date_to: date | None = None
    currency: str | None = None
    tenor: str | None = None
    page: int = 1
    page_size: int = 100


class FxImpliedRateListResponse(BaseModel):
    """Paginated response for FX implied rate queries."""

    data: list[FxImpliedRateRead]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Coverage Summary
# ---------------------------------------------------------------------------


class CurveCoverageSummary(BaseModel):
    """High-level data coverage information for a curve."""

    total_records: int = 0
    date_from: date | None = None
    date_to: date | None = None
    currency_count: int = 0
    currencies: list[str] = []
    tenors: list[str] = []
    last_updated: datetime | None = None


# ---------------------------------------------------------------------------
# Crawl Result
# ---------------------------------------------------------------------------


class CrawlResult(BaseModel):
    """Result of a background crawl operation."""

    status: str  # "success", "partial", "error"
    dates_fetched: list[date] = []
    dates_skipped: list[date] = []
    records_added: int = 0
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Upload Result
# ---------------------------------------------------------------------------


class UploadResult(BaseModel):
    """Result of a manual XLSX upload."""

    records_added: int = 0
    message: str = ""
