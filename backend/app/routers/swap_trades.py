"""
Swap trade API routes — CRUD and Excel import.

CRUD endpoints at /api/v1/swap-trades:
  GET    /              — list with pagination, filtering, sorting
  GET    /{id}          — get single swap trade
  POST   /              — create swap trade manually
  PUT    /{id}          — update swap trade
  DELETE /{id}          — delete swap trade
  POST   /batch-delete  — batch delete swap trades

Import endpoints at /api/v1/imports/swap:
  POST   /upload        — upload Excel, parse, validate, import
  GET    /columns       — get swap column mapping reference
"""

import os
import tempfile
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import ImportLog, SwapTrade
from app.routers._crud import (
    CrudConfig,
    apply_to_both,
    build_crud_router,
    build_list_response,
    derive_ccy_if_missing,
    derive_ccy_if_pair_changed,
)
from app.schemas.import_ import ImportConfirmResponse, ImportParsedRow
from app.schemas.swap_trade import (
    SwapTradeCreate,
    SwapTradeListResponse,
    SwapTradeRead,
    SwapTradeUpdate,
)
from app.services.swap_import_service import swap_import_service
from app.utils.date_utils import utc_now

# ── CRUD Router ──────────────────────────────────────────────────────────────────

router = build_crud_router(
    CrudConfig(
        model=SwapTrade,
        read_schema=SwapTradeRead,
        create_schema=SwapTradeCreate,
        update_schema=SwapTradeUpdate,
        list_response_schema=SwapTradeListResponse,
        prefix="/api/v1/swap-trades",
        tags=["swap-trades"],
        entity_label="Swap trade",
        default_sort="trade_date",
        default_sort_order="desc",
        pre_create_hook=derive_ccy_if_missing,
        pre_update_hook=derive_ccy_if_pair_changed,
    )
)


@router.get("", response_model=SwapTradeListResponse)
def list_swap_trades(
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
    near_value_date_from: date | None = Query(default=None),
    near_value_date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> SwapTradeListResponse:
    """List swap trades with pagination, filtering, and sorting."""

    query = select(SwapTrade)
    count_query = select(func.count(SwapTrade.id))

    if portfolio_id is not None:
        query, count_query = apply_to_both(query, count_query, SwapTrade.portfolio_id == portfolio_id)
    if counterparty_id is not None:
        query, count_query = apply_to_both(query, count_query, SwapTrade.counterparty_id == counterparty_id)
    if ccy_pair:
        query, count_query = apply_to_both(query, count_query, SwapTrade.ccy_pair == ccy_pair)
    if direction:
        query, count_query = apply_to_both(query, count_query, SwapTrade.direction == direction)
    if event_type:
        query, count_query = apply_to_both(query, count_query, SwapTrade.event_type == event_type)
    if trade_date_from:
        query, count_query = apply_to_both(query, count_query, SwapTrade.trade_date >= trade_date_from)
    if trade_date_to:
        query, count_query = apply_to_both(query, count_query, SwapTrade.trade_date <= trade_date_to)
    if near_value_date_from:
        query, count_query = apply_to_both(query, count_query, SwapTrade.near_value_date >= near_value_date_from)
    if near_value_date_to:
        query, count_query = apply_to_both(query, count_query, SwapTrade.near_value_date <= near_value_date_to)
    if search:
        search_term = f"%{search}%"
        cond = (
            (SwapTrade.trade_id.ilike(search_term))
            | (SwapTrade.counterparty_name.ilike(search_term))
            | (SwapTrade.portfolio_name.ilike(search_term))
            | (SwapTrade.ccy_pair.ilike(search_term))
        )
        query, count_query = apply_to_both(query, count_query, cond)

    return build_list_response(
        session,
        SwapTrade,
        SwapTradeRead,
        SwapTradeListResponse,
        query,
        count_query,
        sort_by=sort_by,
        sort_order=sort_order,
        default_sort_col=SwapTrade.trade_date,
        page=page,
        page_size=page_size,
    )


# ── Import Router ─────────────────────────────────────────────────────────────────

import_router = APIRouter(prefix="/api/v1/imports/swap", tags=["swap-import"])


@import_router.post("/upload")
async def upload_swap_excel(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportConfirmResponse:
    """
    Upload a swap trade Excel file, parse, validate, and import into database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = os.path.splitext(file.filename)[1] or ".xls"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Phase 1: Parse
        parsed = swap_import_service.parse_file(tmp_path)

        # Phase 2: Validate
        validated = swap_import_service.validate(parsed)

        # Create initial import log
        import_log = ImportLog(
            filename=file.filename,
            file_hash=parsed.file_hash,
            total_rows=parsed.total_rows,
            status="validated",
            started_at=utc_now(),
            completed_at=utc_now(),
            import_type="swap",
        )
        session.add(import_log)
        session.commit()
        session.refresh(import_log)

        # Phase 3: Execute import
        import_log = swap_import_service.execute_import(
            parsed, validated, import_log, session
        )

        # Build parsed rows for preview
        preview_rows: list[ImportParsedRow] = []
        row_count = min(len(parsed.rows), 100)
        for i in range(row_count):
            row = parsed.rows[i]
            trade_id = row.get("成交编号", "") or row.get("trade_id", "")
            row_errors: list[str] = []
            for err in validated.errors:
                if err.row_number == i + 3:
                    row_errors.append(err.message)
            preview_rows.append(
                ImportParsedRow(
                    row_number=i + 3,
                    trade_id=trade_id if trade_id else None,
                    data=row,
                    errors=row_errors,
                )
            )

        return ImportConfirmResponse(
            import_log_id=import_log.id,
            filename=file.filename,
            total_rows=import_log.total_rows,
            imported_rows=import_log.imported_rows,
            skipped_rows=import_log.skipped_rows,
            error_rows=import_log.error_rows,
            status=import_log.status,
            errors=[e.to_dict() for e in validated.errors[:50]],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@import_router.get("/columns")
def get_swap_column_mapping() -> dict:
    """Get the expected column mapping reference for swap trade ComStar exports."""
    from app.utils.swap_column_mapping import CSV_TO_SWAP_FIELD

    return {
        "mapping": CSV_TO_SWAP_FIELD,
        "total_columns": len(CSV_TO_SWAP_FIELD),
    }
