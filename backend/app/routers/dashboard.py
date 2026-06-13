from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.trade import Trade
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    session: Session = Depends(get_session),
) -> DashboardSummary:
    """Get aggregate summary for the dashboard."""
    from app.models.portfolio import Portfolio
    from app.models.counterparty import Counterparty

    total_trades = session.exec(select(func.count(Trade.id))).one()
    total_portfolios = session.exec(select(func.count(Portfolio.id))).one()
    total_counterparties = session.exec(select(func.count(Counterparty.id))).one()

    # Notional by ccy_pair
    trades = session.exec(
        select(Trade.ccy_pair, func.sum(Trade.notional1).label("total_notional"))
        .where(Trade.notional1.isnot(None))
        .group_by(Trade.ccy_pair)
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
        select(Trade.trade_type, func.count(Trade.id))
        .where(Trade.trade_type.isnot(None))
        .group_by(Trade.trade_type)
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
