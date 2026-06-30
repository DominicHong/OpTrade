from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Portfolio, OptionTrade
from app.schemas.option_trade import (
    OptionTradeCreate,
    OptionTradeFilterParams,
    OptionTradeListResponse,
    OptionTradeRead,
    OptionTradeUpdate,
)

router = APIRouter(prefix="/api/v1/option-trades", tags=["option-trades"])


def _resolve_portfolio(portfolio_id: int | None, portfolio_name: str | None, session: Session) -> tuple[int | None, str | None]:
    """Resolve portfolio_name to portfolio_id. Errors if name given but not found.
    Returns (portfolio_id, portfolio_name) tuple.
    """
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


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/batch-delete")
def batch_delete_option_trades(
    req: BatchDeleteRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete multiple option trades by their database IDs."""
    if not req.ids:
        raise HTTPException(status_code=400, detail="No trade IDs provided")
    deleted = 0
    for tid in req.ids:
        trade = session.get(OptionTrade, tid)
        if trade:
            session.delete(trade)
            deleted += 1
    session.commit()
    return {"status": "deleted", "count": str(deleted)}


@router.get("", response_model=OptionTradeListResponse)
def list_option_trades(
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
    option_category: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> OptionTradeListResponse:
    """List option trades with pagination, filtering, and sorting."""

    # Build base query
    query = select(OptionTrade)
    count_query = select(func.count(OptionTrade.id))

    # Apply filters
    if portfolio_id is not None:
        query = query.where(OptionTrade.portfolio_id == portfolio_id)
        count_query = count_query.where(OptionTrade.portfolio_id == portfolio_id)
    if counterparty_id is not None:
        query = query.where(OptionTrade.counterparty_id == counterparty_id)
        count_query = count_query.where(OptionTrade.counterparty_id == counterparty_id)
    if ccy_pair:
        query = query.where(OptionTrade.ccy_pair == ccy_pair)
        count_query = count_query.where(OptionTrade.ccy_pair == ccy_pair)
    if option_type:
        query = query.where(OptionTrade.option_type == option_type)
        count_query = count_query.where(OptionTrade.option_type == option_type)
    if trade_type:
        query = query.where(OptionTrade.trade_type == trade_type)
        count_query = count_query.where(OptionTrade.trade_type == trade_type)
    if direction:
        query = query.where(OptionTrade.direction == direction)
        count_query = count_query.where(OptionTrade.direction == direction)
    if expiry_from:
        query = query.where(OptionTrade.expiry_date >= expiry_from)
        count_query = count_query.where(OptionTrade.expiry_date >= expiry_from)
    if expiry_to:
        query = query.where(OptionTrade.expiry_date <= expiry_to)
        count_query = count_query.where(OptionTrade.expiry_date <= expiry_to)
    if trade_date_from:
        query = query.where(OptionTrade.trade_date >= trade_date_from)
        count_query = count_query.where(OptionTrade.trade_date >= trade_date_from)
    if trade_date_to:
        query = query.where(OptionTrade.trade_date <= trade_date_to)
        count_query = count_query.where(OptionTrade.trade_date <= trade_date_to)
    if exercise_status:
        query = query.where(OptionTrade.exercise_status == exercise_status)
        count_query = count_query.where(OptionTrade.exercise_status == exercise_status)
    if option_category:
        query = query.where(OptionTrade.option_category == option_category)
        count_query = count_query.where(OptionTrade.option_category == option_category)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (OptionTrade.trade_id.ilike(search_term))
            | (OptionTrade.source_trade_id.ilike(search_term))
            | (OptionTrade.counterparty_name.ilike(search_term))
            | (OptionTrade.portfolio_name.ilike(search_term))
            | (OptionTrade.ccy_pair.ilike(search_term))
        )
        count_query = count_query.where(
            (OptionTrade.trade_id.ilike(search_term))
            | (OptionTrade.source_trade_id.ilike(search_term))
            | (OptionTrade.counterparty_name.ilike(search_term))
            | (OptionTrade.portfolio_name.ilike(search_term))
            | (OptionTrade.ccy_pair.ilike(search_term))
        )

    # Get total count
    total = session.exec(count_query).one()

    # Apply sorting
    sort_column = getattr(OptionTrade, sort_by, OptionTrade.trade_id)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    trades = session.exec(query).all()

    return OptionTradeListResponse(
        data=[OptionTradeRead.model_validate(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{id}", response_model=OptionTradeRead)
def get_option_trade(
    id: int,
    session: Session = Depends(get_session),
) -> OptionTradeRead:
    """Get a single option trade by its database ID."""
    trade = session.get(OptionTrade, id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"OptionTrade {id} not found")
    return OptionTradeRead.model_validate(trade)


@router.post("", response_model=OptionTradeRead, status_code=201)
def create_option_trade(
    data: OptionTradeCreate,
    session: Session = Depends(get_session),
) -> OptionTradeRead:
    """Create a new option trade manually."""
    # Check for duplicate trade_id
    existing = session.exec(
        select(OptionTrade).where(OptionTrade.trade_id == data.trade_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Option trade with trade_id '{data.trade_id}' already exists")

    # Resolve portfolio_name → portfolio_id (no auto-create from this endpoint)
    pid, pname = _resolve_portfolio(data.portfolio_id, data.portfolio_name, session)

    trade_data = data.model_dump()
    trade_data["portfolio_id"] = pid
    trade_data["portfolio_name"] = pname

    trade = OptionTrade(**trade_data)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    return OptionTradeRead.model_validate(trade)


@router.put("/{id}", response_model=OptionTradeRead)
def update_option_trade(
    id: int,
    update: OptionTradeUpdate,
    session: Session = Depends(get_session),
) -> OptionTradeRead:
    """Update mutable fields of an option trade."""
    trade = session.get(OptionTrade, id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"OptionTrade {id} not found")

    update_data = update.model_dump(exclude_unset=True)

    # Resolve portfolio_name → portfolio_id if provided
    pid = update_data.get("portfolio_id")
    pname = update_data.get("portfolio_name")
    if "portfolio_id" in update_data or "portfolio_name" in update_data:
        resolved_id, resolved_name = _resolve_portfolio(pid, pname, session)
        update_data["portfolio_id"] = resolved_id
        update_data["portfolio_name"] = resolved_name

    for key, value in update_data.items():
        setattr(trade, key, value)

    session.add(trade)
    session.commit()
    session.refresh(trade)

    return OptionTradeRead.model_validate(trade)


@router.delete("/{id}")
def delete_option_trade(
    id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete an option trade."""
    trade = session.get(OptionTrade, id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"OptionTrade {id} not found")
    session.delete(trade)
    session.commit()
    return {"status": "deleted", "trade_id": str(id)}
