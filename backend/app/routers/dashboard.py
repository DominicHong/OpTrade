from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Counterparty, Portfolio, OptionTrade
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    session: Session = Depends(get_session),
) -> DashboardSummary:
    """Get aggregate summary for the dashboard."""

    total_trades = session.exec(select(func.count(OptionTrade.id))).one()
    total_portfolios = session.exec(select(func.count(Portfolio.id))).one()
    total_counterparties = session.exec(select(func.count(Counterparty.id))).one()

    # Notional by ccy_pair
    trades = session.exec(
        select(OptionTrade.ccy_pair, func.sum(OptionTrade.notional1).label("total_notional"))
        .where(OptionTrade.notional1.isnot(None))
        .group_by(OptionTrade.ccy_pair)
    ).all()

    notional_by_ccy: dict[str, float] = {}
    total_notional: float = 0.0
    for row in trades:
        if row[0]:
            val = float(row[1] or 0)
            notional_by_ccy[row[0]] = val
            total_notional += val

    # Trades by type
    type_counts = session.exec(
        select(OptionTrade.trade_type, func.count(OptionTrade.id))
        .where(OptionTrade.trade_type.isnot(None))
        .group_by(OptionTrade.trade_type)
    ).all()
    trades_by_type = {row[0]: row[1] for row in type_counts if row[0]}

    return DashboardSummary(
        total_trades=total_trades,
        total_portfolios=total_portfolios,
        total_counterparties=total_counterparties,
        total_notional1=total_notional,
        notional_by_ccy=notional_by_ccy,
        trades_by_type=trades_by_type,
    )
