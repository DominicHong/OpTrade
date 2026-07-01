from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas.portfolio import (
    AggregatedAnalysisRequest,
    AggregatedAnalysisResponse,
    PortfolioCreate,
    PortfolioGreeksRequest,
    PortfolioGreeksResponse,
    PortfolioRead,
    PortfolioResolveRequest,
    PortfolioResolveResponse,
    PortfolioUpdate,
)
from app.services.portfolio_service import PortfolioService, get_portfolio_service

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])


def _service(
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioService:
    return service


@router.get("", response_model=list[PortfolioRead])
def list_portfolios(
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> list[PortfolioRead]:
    """List all portfolios with trade counts."""
    return service.list_portfolios(session)


@router.post("", response_model=PortfolioRead, status_code=201)
def create_portfolio(
    data: PortfolioCreate,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> PortfolioRead:
    """Create a new portfolio."""
    return service.create_portfolio(session, data)


@router.get("/earliest-trade-date")
def get_earliest_trade_date(
    portfolio_ids: str,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> dict[str, str | None]:
    """Return the earliest trade_date across selected portfolios.

    ``portfolio_ids`` is a comma-separated list of portfolio IDs.
    """
    try:
        ids = [int(x.strip()) for x in portfolio_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid portfolio_ids format")
    if not ids:
        raise HTTPException(status_code=400, detail="At least one portfolio_id is required")

    earliest = service._find_earliest_trade_date(session, ids)
    return {"earliest_trade_date": earliest.isoformat() if earliest else None}


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> PortfolioRead:
    """Get a single portfolio."""
    return service.get_portfolio(session, portfolio_id)


@router.put("/{portfolio_id}", response_model=PortfolioRead)
def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> PortfolioRead:
    """Update a portfolio."""
    return service.update_portfolio(session, portfolio_id, data)


@router.delete("/{portfolio_id}")
def delete_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> dict[str, str]:
    """Delete a portfolio (rejects if it has trades)."""
    service.delete_portfolio(session, portfolio_id)
    return {"status": "deleted", "portfolio_id": str(portfolio_id)}


@router.post("/{portfolio_id}/resolve-params", response_model=PortfolioResolveResponse)
def resolve_portfolio_params(
    portfolio_id: int,
    request: PortfolioResolveRequest,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> PortfolioResolveResponse:
    """Resolve curve-based valuation parameters for every trade in a portfolio.

    For each trade, interpolates risk-free rates from the FX implied rate
    curve at the trade's remaining maturity, looks up the spot rate, and
    computes historical volatility from the past 250 trading days.

    Only applies to CNY-quoted currency pairs (USD/CNY, EUR/CNY, etc.).
    """
    return service.resolve_portfolio_params(session, portfolio_id, request)


@router.post("/{portfolio_id}/greeks", response_model=PortfolioGreeksResponse)
def calculate_portfolio_greeks(
    portfolio_id: int,
    request: PortfolioGreeksRequest,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> PortfolioGreeksResponse:
    """Calculate aggregated Greeks (Delta, Gamma, NPV) for all trades in a portfolio.

    When ``curve_type`` is ``"fx_implied_rate"``, per-trade rates are
    interpolated from the FX implied rate curve.  User overrides in
    ``trade_params`` take priority over curve-derived values.
    """
    return service.calculate_greeks(session, portfolio_id, request)


@router.post("/aggregate", response_model=AggregatedAnalysisResponse)
def calculate_aggregated_analysis(
    request: AggregatedAnalysisRequest,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> AggregatedAnalysisResponse:
    """Calculate aggregated P&L across multiple portfolios.

    Accepts multiple portfolio IDs and a date range (start_date to valuation_date).
    Computes option P&L with exercise-aware logic and spot trade P&L using
    curve-derived market rates.  Supported currency pairs: USD/CNY, EUR/CNY,
    GBP/CNY, HKD/CNY, JPY/CNY.
    """
    if not request.portfolio_ids:
        raise HTTPException(status_code=400, detail="At least one portfolio_id is required")
    return service.calculate_aggregated_analysis(session, request)
