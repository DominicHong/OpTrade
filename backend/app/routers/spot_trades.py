"""
Spot trade API routes — CRUD and Excel import.

CRUD endpoints at /api/v1/spot-trades:
  GET    /              — list with pagination, filtering, sorting
  GET    /{id}          — get single spot trade
  POST   /              — create spot trade manually
  PUT    /{id}          — update spot trade
  DELETE /{id}          — delete spot trade
  POST   /batch-delete  — batch delete spot trades

Import endpoints at /api/v1/imports/spot:
  POST   /upload        — upload Excel, parse, validate, import
  GET    /columns       — get spot column mapping reference
"""

from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import SpotTrade
from app.routers._crud import (
    CrudConfig,
    apply_to_both,
    build_crud_router,
    build_list_response,
    derive_ccy_if_missing,
    derive_ccy_if_pair_changed,
)
from app.schemas.import_ import ImportConfirmResponse
from app.schemas.spot_trade import (
    SpotTradeCreate,
    SpotTradeListResponse,
    SpotTradeRead,
    SpotTradeUpdate,
)
from app.services.import_pipeline import column_mapping_response, run_upload
from app.services.spot_import_service import spot_import_service
from app.utils.spot_column_mapping import CSV_TO_SPOT_FIELD

# ── CRUD Router ──────────────────────────────────────────────────────────────────

router = build_crud_router(
    CrudConfig(
        model=SpotTrade,
        read_schema=SpotTradeRead,
        create_schema=SpotTradeCreate,
        update_schema=SpotTradeUpdate,
        list_response_schema=SpotTradeListResponse,
        prefix="/api/v1/spot-trades",
        tags=["spot-trades"],
        entity_label="Spot trade",
        default_sort="trade_date",
        default_sort_order="desc",
        pre_create_hook=derive_ccy_if_missing,
        pre_update_hook=derive_ccy_if_pair_changed,
    )
)


@router.get("", response_model=SpotTradeListResponse)
def list_spot_trades(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500, alias="page_size"),
    sort_by: str = Query(default="trade_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    portfolio_id: int | None = Query(default=None),
    counterparty_id: int | None = Query(default=None),
    ccy_pair: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    trade_date_from: date | None = Query(default=None),
    trade_date_to: date | None = Query(default=None),
    settlement_date_from: date | None = Query(default=None),
    settlement_date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> SpotTradeListResponse:
    """List spot trades with pagination, filtering, and sorting."""

    query = select(SpotTrade)
    count_query = select(func.count(SpotTrade.id))

    if portfolio_id is not None:
        query, count_query = apply_to_both(query, count_query, SpotTrade.portfolio_id == portfolio_id)
    if counterparty_id is not None:
        query, count_query = apply_to_both(query, count_query, SpotTrade.counterparty_id == counterparty_id)
    if ccy_pair:
        query, count_query = apply_to_both(query, count_query, SpotTrade.ccy_pair == ccy_pair)
    if direction:
        query, count_query = apply_to_both(query, count_query, SpotTrade.direction == direction)
    if event_type:
        query, count_query = apply_to_both(query, count_query, SpotTrade.event_type == event_type)
    if trade_date_from:
        query, count_query = apply_to_both(query, count_query, SpotTrade.trade_date >= trade_date_from)
    if trade_date_to:
        query, count_query = apply_to_both(query, count_query, SpotTrade.trade_date <= trade_date_to)
    if settlement_date_from:
        query, count_query = apply_to_both(query, count_query, SpotTrade.settlement_date >= settlement_date_from)
    if settlement_date_to:
        query, count_query = apply_to_both(query, count_query, SpotTrade.settlement_date <= settlement_date_to)
    if search:
        search_term = f"%{search}%"
        cond = (
            (SpotTrade.trade_id.ilike(search_term))
            | (SpotTrade.counterparty_name.ilike(search_term))
            | (SpotTrade.portfolio_name.ilike(search_term))
            | (SpotTrade.ccy_pair.ilike(search_term))
        )
        query, count_query = apply_to_both(query, count_query, cond)

    return build_list_response(
        session,
        SpotTrade,
        SpotTradeRead,
        SpotTradeListResponse,
        query,
        count_query,
        sort_by=sort_by,
        sort_order=sort_order,
        default_sort_col=SpotTrade.trade_date,
        page=page,
        page_size=page_size,
    )


# ── Import Router ─────────────────────────────────────────────────────────────────

import_router = APIRouter(prefix="/api/v1/imports/spot", tags=["spot-import"])


@import_router.post("/upload")
async def upload_spot_excel(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportConfirmResponse:
    """Upload a spot trade Excel file, parse, validate, and import into database."""
    return await run_upload(
        file, spot_import_service, session,
        import_type="spot", default_suffix=".xls",
    )


@import_router.get("/columns")
def get_spot_column_mapping() -> dict:
    """Get the expected column mapping reference for spot trade ComStar exports."""
    return column_mapping_response(CSV_TO_SPOT_FIELD)
