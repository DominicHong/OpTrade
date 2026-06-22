from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioGreeksRequest,
    PortfolioGreeksResponse,
    PortfolioRead,
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


@router.post("/{portfolio_id}/greeks", response_model=PortfolioGreeksResponse)
def calculate_portfolio_greeks(
    portfolio_id: int,
    request: PortfolioGreeksRequest,
    session: Session = Depends(get_session),
    service: PortfolioService = Depends(_service),
) -> PortfolioGreeksResponse:
    """Calculate aggregated Greeks (Delta, Gamma) for all trades in a portfolio."""
    return service.calculate_greeks(session, portfolio_id, request)
