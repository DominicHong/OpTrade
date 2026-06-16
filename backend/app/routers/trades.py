from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.trade import Trade
from app.schemas.trade import TradeCreate, TradeFilterParams, TradeListResponse, TradeRead, TradeUpdate

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/batch-delete")
def batch_delete_trades(
    req: BatchDeleteRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete multiple trades by their database IDs."""
    if not req.ids:
        raise HTTPException(status_code=400, detail="No trade IDs provided")
    deleted = 0
    for trade_id in req.ids:
        trade = session.get(Trade, trade_id)
        if trade:
            session.delete(trade)
            deleted += 1
    session.commit()
    return {"status": "deleted", "count": str(deleted)}


@router.get("", response_model=TradeListResponse)
def list_trades(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500, alias="page_size"),
    sort_by: str = Query(default="trade_id"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    portfolio_id: int | None = Query(default=None),
    counterparty_id: int | None = Query(default=None),
    ccy_pair: str | None = Query(default=None),
    option_type: str | None = Query(default=None),
    trade_type: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    expiry_from: date | None = Query(default=None),
    expiry_to: date | None = Query(default=None),
    trade_date_from: date | None = Query(default=None),
    trade_date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    exercise_status: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> TradeListResponse:
    """List trades with pagination, filtering, and sorting."""

    # Build base query
    query = select(Trade)
    count_query = select(func.count(Trade.id))

    # Apply filters
    if portfolio_id is not None:
        query = query.where(Trade.portfolio_id == portfolio_id)
        count_query = count_query.where(Trade.portfolio_id == portfolio_id)
    if counterparty_id is not None:
        query = query.where(Trade.counterparty_id == counterparty_id)
        count_query = count_query.where(Trade.counterparty_id == counterparty_id)
    if ccy_pair:
        query = query.where(Trade.ccy_pair == ccy_pair)
        count_query = count_query.where(Trade.ccy_pair == ccy_pair)
    if option_type:
        query = query.where(Trade.option_type == option_type)
        count_query = count_query.where(Trade.option_type == option_type)
    if trade_type:
        query = query.where(Trade.trade_type == trade_type)
        count_query = count_query.where(Trade.trade_type == trade_type)
    if direction:
        query = query.where(Trade.direction == direction)
        count_query = count_query.where(Trade.direction == direction)
    if expiry_from:
        query = query.where(Trade.expiry_date >= expiry_from)
        count_query = count_query.where(Trade.expiry_date >= expiry_from)
    if expiry_to:
        query = query.where(Trade.expiry_date <= expiry_to)
        count_query = count_query.where(Trade.expiry_date <= expiry_to)
    if trade_date_from:
        query = query.where(Trade.trade_date >= trade_date_from)
        count_query = count_query.where(Trade.trade_date >= trade_date_from)
    if trade_date_to:
        query = query.where(Trade.trade_date <= trade_date_to)
        count_query = count_query.where(Trade.trade_date <= trade_date_to)
    if exercise_status:
        query = query.where(Trade.exercise_status == exercise_status)
        count_query = count_query.where(Trade.exercise_status == exercise_status)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Trade.trade_id.ilike(search_term))
            | (Trade.source_trade_id.ilike(search_term))
            | (Trade.counterparty_name.ilike(search_term))
            | (Trade.portfolio_name.ilike(search_term))
            | (Trade.ccy_pair.ilike(search_term))
        )
        count_query = count_query.where(
            (Trade.trade_id.ilike(search_term))
            | (Trade.source_trade_id.ilike(search_term))
            | (Trade.counterparty_name.ilike(search_term))
            | (Trade.portfolio_name.ilike(search_term))
            | (Trade.ccy_pair.ilike(search_term))
        )

    # Get total count
    total = session.exec(count_query).one()

    # Apply sorting
    sort_column = getattr(Trade, sort_by, Trade.trade_id)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    trades = session.exec(query).all()

    return TradeListResponse(
        data=[TradeRead.model_validate(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{trade_id}", response_model=TradeRead)
def get_trade(
    trade_id: int,
    session: Session = Depends(get_session),
) -> TradeRead:
    """Get a single trade by its database ID."""
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    return TradeRead.model_validate(trade)


@router.post("", response_model=TradeRead, status_code=201)
def create_trade(
    data: TradeCreate,
    session: Session = Depends(get_session),
) -> TradeRead:
    """Create a new trade manually."""
    # Check for duplicate trade_id
    existing = session.exec(
        select(Trade).where(Trade.trade_id == data.trade_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Trade with trade_id '{data.trade_id}' already exists")

    trade = Trade(**data.model_dump())
    session.add(trade)
    session.commit()
    session.refresh(trade)
    return TradeRead.model_validate(trade)


@router.put("/{trade_id}", response_model=TradeRead)
def update_trade(
    trade_id: int,
    update: TradeUpdate,
    session: Session = Depends(get_session),
) -> TradeRead:
    """Update mutable fields of a trade."""
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(trade, key, value)

    session.add(trade)
    session.commit()
    session.refresh(trade)

    return TradeRead.model_validate(trade)


@router.delete("/{trade_id}")
def delete_trade(
    trade_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete a trade."""
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    session.delete(trade)
    session.commit()
    return {"status": "deleted", "trade_id": str(trade_id)}
