from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import OptionTrade
from app.routers._crud import (
    CrudConfig,
    apply_to_both,
    build_crud_router,
    build_list_response,
)
from app.schemas.option_trade import (
    OptionTradeCreate,
    OptionTradeListResponse,
    OptionTradeRead,
    OptionTradeUpdate,
)

router = build_crud_router(
    CrudConfig(
        model=OptionTrade,
        read_schema=OptionTradeRead,
        create_schema=OptionTradeCreate,
        update_schema=OptionTradeUpdate,
        list_response_schema=OptionTradeListResponse,
        prefix="/api/v1/option-trades",
        tags=["option-trades"],
        entity_label="OptionTrade",
        default_sort="trade_id",
        default_sort_order="asc",
    )
)


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

    query = select(OptionTrade)
    count_query = select(func.count(OptionTrade.id))

    if portfolio_id is not None:
        query, count_query = apply_to_both(query, count_query, OptionTrade.portfolio_id == portfolio_id)
    if counterparty_id is not None:
        query, count_query = apply_to_both(query, count_query, OptionTrade.counterparty_id == counterparty_id)
    if ccy_pair:
        query, count_query = apply_to_both(query, count_query, OptionTrade.ccy_pair == ccy_pair)
    if option_type:
        query, count_query = apply_to_both(query, count_query, OptionTrade.option_type == option_type)
    if trade_type:
        query, count_query = apply_to_both(query, count_query, OptionTrade.trade_type == trade_type)
    if direction:
        query, count_query = apply_to_both(query, count_query, OptionTrade.direction == direction)
    if expiry_from:
        query, count_query = apply_to_both(query, count_query, OptionTrade.expiry_date >= expiry_from)
    if expiry_to:
        query, count_query = apply_to_both(query, count_query, OptionTrade.expiry_date <= expiry_to)
    if trade_date_from:
        query, count_query = apply_to_both(query, count_query, OptionTrade.trade_date >= trade_date_from)
    if trade_date_to:
        query, count_query = apply_to_both(query, count_query, OptionTrade.trade_date <= trade_date_to)
    if exercise_status:
        query, count_query = apply_to_both(query, count_query, OptionTrade.exercise_status == exercise_status)
    if option_category:
        query, count_query = apply_to_both(query, count_query, OptionTrade.option_category == option_category)
    if search:
        search_term = f"%{search}%"
        cond = (
            (OptionTrade.trade_id.ilike(search_term))
            | (OptionTrade.source_trade_id.ilike(search_term))
            | (OptionTrade.counterparty_name.ilike(search_term))
            | (OptionTrade.portfolio_name.ilike(search_term))
            | (OptionTrade.ccy_pair.ilike(search_term))
        )
        query, count_query = apply_to_both(query, count_query, cond)

    return build_list_response(
        session,
        OptionTrade,
        OptionTradeRead,
        OptionTradeListResponse,
        query,
        count_query,
        sort_by=sort_by,
        sort_order=sort_order,
        default_sort_col=OptionTrade.trade_id,
        page=page,
        page_size=page_size,
    )
