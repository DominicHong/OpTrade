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

import os
import tempfile
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import ImportLog, SpotTrade
from app.schemas.import_ import ImportConfirmResponse, ImportParsedRow
from app.schemas.spot_trade import (
    SpotTradeCreate,
    SpotTradeFilterParams,
    SpotTradeListResponse,
    SpotTradeRead,
    SpotTradeUpdate,
)
from app.services.spot_import_service import spot_import_service
from app.utils.ccy_utils import split_ccy_pair
from app.utils.date_utils import utc_now

# ── CRUD Router ──────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1/spot-trades", tags=["spot-trades"])


class BatchDeleteRequest(BaseModel):
    ids: list[int]


def _resolve_portfolio(
    portfolio_id: int | None, portfolio_name: str | None, session: Session
) -> tuple[int | None, str | None]:
    """Resolve portfolio_name to portfolio_id. Errors if name given but not found."""
    from app.models import Portfolio

    if portfolio_id is not None:
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio with id {portfolio_id} not found")
        return portfolio.id, portfolio.name

    if portfolio_name:
        portfolio = session.exec(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        ).first()
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail=f"投组 '{portfolio_name}' 不存在，请先在投组管理页面创建该投组",
            )
        return portfolio.id, portfolio.name

    return None, None


@router.post("/batch-delete")
def batch_delete_spot_trades(
    req: BatchDeleteRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete multiple spot trades by their database IDs."""
    if not req.ids:
        raise HTTPException(status_code=400, detail="No spot trade IDs provided")
    deleted = 0
    for spot_id in req.ids:
        trade = session.get(SpotTrade, spot_id)
        if trade:
            session.delete(trade)
            deleted += 1
    session.commit()
    return {"status": "deleted", "count": str(deleted)}


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
        query = query.where(SpotTrade.portfolio_id == portfolio_id)
        count_query = count_query.where(SpotTrade.portfolio_id == portfolio_id)
    if counterparty_id is not None:
        query = query.where(SpotTrade.counterparty_id == counterparty_id)
        count_query = count_query.where(SpotTrade.counterparty_id == counterparty_id)
    if ccy_pair:
        query = query.where(SpotTrade.ccy_pair == ccy_pair)
        count_query = count_query.where(SpotTrade.ccy_pair == ccy_pair)
    if direction:
        query = query.where(SpotTrade.direction == direction)
        count_query = count_query.where(SpotTrade.direction == direction)
    if event_type:
        query = query.where(SpotTrade.event_type == event_type)
        count_query = count_query.where(SpotTrade.event_type == event_type)
    if trade_date_from:
        query = query.where(SpotTrade.trade_date >= trade_date_from)
        count_query = count_query.where(SpotTrade.trade_date >= trade_date_from)
    if trade_date_to:
        query = query.where(SpotTrade.trade_date <= trade_date_to)
        count_query = count_query.where(SpotTrade.trade_date <= trade_date_to)
    if settlement_date_from:
        query = query.where(SpotTrade.settlement_date >= settlement_date_from)
        count_query = count_query.where(SpotTrade.settlement_date >= settlement_date_from)
    if settlement_date_to:
        query = query.where(SpotTrade.settlement_date <= settlement_date_to)
        count_query = count_query.where(SpotTrade.settlement_date <= settlement_date_to)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (SpotTrade.trade_id.ilike(search_term))
            | (SpotTrade.counterparty_name.ilike(search_term))
            | (SpotTrade.portfolio_name.ilike(search_term))
            | (SpotTrade.ccy_pair.ilike(search_term))
        )
        count_query = count_query.where(
            (SpotTrade.trade_id.ilike(search_term))
            | (SpotTrade.counterparty_name.ilike(search_term))
            | (SpotTrade.portfolio_name.ilike(search_term))
            | (SpotTrade.ccy_pair.ilike(search_term))
        )

    total = session.exec(count_query).one()

    sort_column = getattr(SpotTrade, sort_by, SpotTrade.trade_date)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    trades = session.exec(query).all()

    return SpotTradeListResponse(
        data=[SpotTradeRead.model_validate(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{spot_id}", response_model=SpotTradeRead)
def get_spot_trade(
    spot_id: int,
    session: Session = Depends(get_session),
) -> SpotTradeRead:
    """Get a single spot trade by its database ID."""
    trade = session.get(SpotTrade, spot_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Spot trade {spot_id} not found")
    return SpotTradeRead.model_validate(trade)


@router.post("", response_model=SpotTradeRead, status_code=201)
def create_spot_trade(
    data: SpotTradeCreate,
    session: Session = Depends(get_session),
) -> SpotTradeRead:
    """Create a new spot trade manually."""
    # Check for duplicate trade_id
    existing = session.exec(
        select(SpotTrade).where(SpotTrade.trade_id == data.trade_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Spot trade with trade_id '{data.trade_id}' already exists"
        )

    # Resolve portfolio_name → portfolio_id
    pid, pname = _resolve_portfolio(data.portfolio_id, data.portfolio_name, session)

    # Derive ccy1/ccy2 from ccy_pair
    trade_data = data.model_dump()
    trade_data["portfolio_id"] = pid
    trade_data["portfolio_name"] = pname

    if trade_data.get("ccy_pair") and not (trade_data.get("ccy1") and trade_data.get("ccy2")):
        ccy1, ccy2 = split_ccy_pair(trade_data["ccy_pair"])
        if ccy1 and ccy2:
            trade_data["ccy1"] = ccy1
            trade_data["ccy2"] = ccy2

    trade = SpotTrade(**trade_data)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    return SpotTradeRead.model_validate(trade)


@router.put("/{spot_id}", response_model=SpotTradeRead)
def update_spot_trade(
    spot_id: int,
    update: SpotTradeUpdate,
    session: Session = Depends(get_session),
) -> SpotTradeRead:
    """Update mutable fields of a spot trade."""
    trade = session.get(SpotTrade, spot_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Spot trade {spot_id} not found")

    update_data = update.model_dump(exclude_unset=True)

    # Resolve portfolio_name → portfolio_id if provided
    pid = update_data.get("portfolio_id")
    pname = update_data.get("portfolio_name")
    if "portfolio_id" in update_data or "portfolio_name" in update_data:
        resolved_id, resolved_name = _resolve_portfolio(pid, pname, session)
        update_data["portfolio_id"] = resolved_id
        update_data["portfolio_name"] = resolved_name

    # Derive ccy1/ccy2 if ccy_pair changed
    if update_data.get("ccy_pair"):
        ccy1, ccy2 = split_ccy_pair(update_data["ccy_pair"])
        if ccy1 and ccy2:
            update_data["ccy1"] = ccy1
            update_data["ccy2"] = ccy2

    for key, value in update_data.items():
        setattr(trade, key, value)

    session.add(trade)
    session.commit()
    session.refresh(trade)

    return SpotTradeRead.model_validate(trade)


@router.delete("/{spot_id}")
def delete_spot_trade(
    spot_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete a spot trade."""
    trade = session.get(SpotTrade, spot_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Spot trade {spot_id} not found")
    session.delete(trade)
    session.commit()
    return {"status": "deleted", "trade_id": str(spot_id)}


# ── Import Router ─────────────────────────────────────────────────────────────────

import_router = APIRouter(prefix="/api/v1/imports/spot", tags=["spot-import"])


@import_router.post("/upload")
async def upload_spot_excel(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportConfirmResponse:
    """
    Upload a spot trade Excel file, parse, validate, and import into database.
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
        parsed = spot_import_service.parse_file(tmp_path)

        # Phase 2: Validate
        validated = spot_import_service.validate(parsed)

        # Create initial import log
        import_log = ImportLog(
            filename=file.filename,
            file_hash=parsed.file_hash,
            total_rows=parsed.total_rows,
            status="validated",
            started_at=utc_now(),
            completed_at=utc_now(),
            import_type="spot",
        )
        session.add(import_log)
        session.commit()
        session.refresh(import_log)

        # Note: validation errors are returned inline in the response `errors` field

        # Phase 3: Execute import
        import_log = spot_import_service.execute_import(
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
def get_spot_column_mapping() -> dict:
    """Get the expected column mapping reference for spot trade ComStar exports."""
    from app.utils.spot_column_mapping import CSV_TO_SPOT_FIELD

    return {
        "mapping": CSV_TO_SPOT_FIELD,
        "total_columns": len(CSV_TO_SPOT_FIELD),
    }
