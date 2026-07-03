"""Exchange rate management API routes."""

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.database import get_session
from app.schemas.exchange_rate import (
    ExchangeRateCoverageSummary,
    ExchangeRateFilterParams,
    ExchangeRateImportResult,
    ExchangeRateListResponse,
    ExchangeRateManualCreate,
    ExchangeRateRead,
    ExchangeRateUploadResult,
)
from app.services.exchange_rate_service import (
    ExchangeRateService,
    get_exchange_rate_service,
)

router = APIRouter(prefix="/api/v1/exchange-rates", tags=["exchange-rates"])


# ---------------------------------------------------------------------------
# List / query / export
# ---------------------------------------------------------------------------


@router.get("", response_model=ExchangeRateListResponse)
def list_exchange_rates(
    params: ExchangeRateFilterParams = Depends(),
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> ExchangeRateListResponse:
    """Paginated query of exchange rates with optional filters."""
    return service.query_rates(session, params)


@router.get("/export")
def export_exchange_rates(
    params: ExchangeRateFilterParams = Depends(),
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
):
    """Export all matching exchange rate rows as a CSV file."""
    csv_text = service.export_rates_csv(session, params)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": "attachment; filename=exchange_rates.csv",
        },
    )


@router.get("/coverage", response_model=ExchangeRateCoverageSummary)
def get_exchange_rate_coverage(
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> ExchangeRateCoverageSummary:
    """Return data coverage summary (date range, ccy_pairs, etc.)."""
    return service.get_coverage(session)


@router.get("/ccy-pairs", response_model=list[str])
def list_ccy_pairs(
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> list[str]:
    """List distinct currency pairs present in the data."""
    return service.get_ccy_pairs(session)


# ---------------------------------------------------------------------------
# Import from FX implied rate curve
# ---------------------------------------------------------------------------


@router.post("/import-from-curve", response_model=ExchangeRateImportResult)
def import_from_curve(
    rate_date: date,
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> ExchangeRateImportResult:
    """Derive 9 exchange rates for *rate_date* from the FX implied rate curve.

    Pulls 5 CNY-quoted pairs (USD/CNY, EUR/CNY, HKD/CNY, GBP/CNY, JPY/CNY)
    directly from ``fx_implied_rates.spot_rate`` and derives 4 cross pairs
    (USD/HKD, USD/JPY, EUR/USD, GBP/USD) by division.  Upserts existing rows.
    """
    return service.import_from_fx_implied_curve(session, rate_date)


@router.post("/import-from-curve/all-dates", response_model=ExchangeRateImportResult)
def import_all_dates_from_curve(
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> ExchangeRateImportResult:
    """Backfill exchange rates for every distinct date in fx_implied_rates."""
    from sqlmodel import select, func
    from app.models.curve import FxImpliedRate

    dates = session.exec(
        select(FxImpliedRate.curve_date).distinct().order_by(FxImpliedRate.curve_date.asc())
    ).all()
    if not dates:
        return ExchangeRateImportResult(message="FX implied rate 曲线无任何数据，无可导入日期。")
    return service.import_many_dates_from_fx_implied(session, list(dates))


# ---------------------------------------------------------------------------
# Manual entry
# ---------------------------------------------------------------------------


@router.post("/manual", response_model=ExchangeRateRead, status_code=201)
def create_manual_rate(
    payload: ExchangeRateManualCreate,
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> ExchangeRateRead:
    """Insert or update a single manually-entered exchange rate."""
    return service.create_manual(session, payload)


# ---------------------------------------------------------------------------
# CSV upload
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=ExchangeRateUploadResult, status_code=201)
async def upload_exchange_rates_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> ExchangeRateUploadResult:
    """Upload a CSV file with columns: 日期, 货币对, 汇率 [, 来源]."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only .csv files are accepted.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    return service.process_uploaded_csv(session, content)
