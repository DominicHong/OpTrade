"""Curve management API routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.database import get_session
from app.schemas.curve import (
    CrawlResult,
    CurveCoverageSummary,
    CurveDefinitionRead,
    FxImpliedRateFilterParams,
    FxImpliedRateListResponse,
    UploadResult,
)
from app.services.curve_service import CurveService, get_curve_service

router = APIRouter(prefix="/api/v1/curves", tags=["curves"])


# ---------------------------------------------------------------------------
# Curve Definitions
# ---------------------------------------------------------------------------


@router.get("/definitions", response_model=list[CurveDefinitionRead])
def list_curve_definitions(
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> list[CurveDefinitionRead]:
    """List all available curve types (registry entries)."""
    return service.list_definitions(session)


# ---------------------------------------------------------------------------
# FX Implied Rate — data access
# ---------------------------------------------------------------------------


@router.get("/fx-implied-rates", response_model=FxImpliedRateListResponse)
def list_fx_implied_rates(
    params: FxImpliedRateFilterParams = Depends(),
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> FxImpliedRateListResponse:
    """Paginated query of FX implied rate data with optional filters."""
    return service.query_fx_rates(session, params)


@router.get("/fx-implied-rates/export")
def export_fx_implied_rates(
    params: FxImpliedRateFilterParams = Depends(),
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
):
    """Export all matching FX implied rate data as a CSV file."""
    csv_text = service.export_fx_rates_csv(session, params)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": "attachment; filename=fx_implied_rates.csv",
        },
    )


@router.get("/fx-implied-rates/coverage", response_model=CurveCoverageSummary)
def get_fx_implied_rate_coverage(
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> CurveCoverageSummary:
    """Return data coverage summary (date range, currencies, tenors, etc.)."""
    return service.get_coverage(session)


@router.get("/fx-implied-rates/currencies", response_model=list[str])
def get_fx_implied_currencies(
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> list[str]:
    """List distinct foreign currencies present in the data."""
    return service.get_currencies(session)


@router.get("/fx-implied-rates/tenors", response_model=list[str])
def get_fx_implied_tenors(
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> list[str]:
    """List distinct tenors present in the data."""
    return service.get_tenors(session)


# ---------------------------------------------------------------------------
# Crawl trigger
# ---------------------------------------------------------------------------


@router.post("/fx-implied-rates/refresh", response_model=CrawlResult)
async def refresh_fx_implied_rates(
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> CrawlResult:
    """Trigger a background crawl for missing FX implied rate dates.

    Uses Playwright + MS Edge to automate the chinamoney website export.
    This is a synchronous request — the client waits for the crawl to finish.
    """
    return await service.trigger_crawl(session)


# ---------------------------------------------------------------------------
# Manual XLSX upload (fallback)
# ---------------------------------------------------------------------------


@router.post("/fx-implied-rates/upload", status_code=201)
async def upload_fx_implied_xlsx(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    service: CurveService = Depends(get_curve_service),
) -> UploadResult:
    """Upload a manually-downloaded chinamoney XLSX file.

    Use this as a fallback when the automated crawl cannot reach the
    chinamoney website (e.g., network restrictions or page changes).
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx and .xls files are accepted.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    return service.process_uploaded_xlsx(session, content)
