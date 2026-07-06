from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Counterparty, CurveDefinition, Portfolio, OptionTrade, SpotTrade, SwapTrade
from app.schemas.dashboard import (
    DashboardAnalysisRequest,
    DashboardDefaultsResponse,
    DashboardSummary,
)
from app.schemas.portfolio import AggregatedAnalysisRequest, AggregatedAnalysisResponse
from app.services.portfolio_service import PortfolioService, get_portfolio_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _get_service(
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioService:
    return service


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    session: Session = Depends(get_session),
) -> DashboardSummary:
    """Get aggregate summary for the dashboard."""

    option_trade_count = session.exec(select(func.count(OptionTrade.id))).one()
    spot_trade_count = session.exec(select(func.count(SpotTrade.id))).one()
    swap_trade_count = session.exec(select(func.count(SwapTrade.id))).one()
    total_portfolios = session.exec(select(func.count(Portfolio.id))).one()

    # Unique counterparties across option, spot and swap trades
    opt_cp_ids = set(
        session.exec(
            select(OptionTrade.counterparty_id).where(
                OptionTrade.counterparty_id.isnot(None)
            )
        ).all()
    )
    spot_cp_ids = set(
        session.exec(
            select(SpotTrade.counterparty_id).where(
                SpotTrade.counterparty_id.isnot(None)
            )
        ).all()
    )
    swap_cp_ids = set(
        session.exec(
            select(SwapTrade.counterparty_id).where(
                SwapTrade.counterparty_id.isnot(None)
            )
        ).all()
    )
    total_counterparties = len(opt_cp_ids | spot_cp_ids | swap_cp_ids)

    return DashboardSummary(
        option_trade_count=option_trade_count,
        spot_trade_count=spot_trade_count,
        swap_trade_count=swap_trade_count,
        total_portfolios=total_portfolios,
        total_counterparties=total_counterparties,
    )


@router.post("/analysis", response_model=AggregatedAnalysisResponse)
def calculate_dashboard_analysis(
    request: DashboardAnalysisRequest,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_get_service),
) -> AggregatedAnalysisResponse:
    """Calculate aggregated P&L analysis for ALL portfolios.

    Automatically includes every portfolio in the system.  Does NOT accept
    per-trade parameter overrides — curve derivation uses default values.
    """
    all_portfolio_ids = session.exec(select(Portfolio.id)).all()

    agg_request = AggregatedAnalysisRequest(
        portfolio_ids=list(all_portfolio_ids),
        start_date=request.start_date,
        valuation_date=request.valuation_date,
        curve_type=request.curve_type,
    )
    return service.calculate_aggregated_analysis(session, agg_request)


@router.get("/defaults", response_model=DashboardDefaultsResponse)
def get_dashboard_defaults(
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_get_service),
) -> DashboardDefaultsResponse:
    """Return default start_date and curve_type for the dashboard analysis form.

    - ``earliest_trade_date``: the earliest trade_date across ALL portfolios.
    - ``curve_type``: the first active curve definition's curve_type.
    """
    all_portfolio_ids = session.exec(select(Portfolio.id)).all()
    earliest = (
        service._find_earliest_trade_date(session, list(all_portfolio_ids))
        if all_portfolio_ids
        else None
    )

    first_curve = session.exec(
        select(CurveDefinition)
        .where(CurveDefinition.is_active == True)  # noqa: E712
        .order_by(CurveDefinition.id)
    ).first()
    curve_type = first_curve.curve_type if first_curve else None

    return DashboardDefaultsResponse(
        earliest_trade_date=earliest.isoformat() if earliest else None,
        curve_type=curve_type,
    )
