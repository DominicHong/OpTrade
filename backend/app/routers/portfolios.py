from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.portfolio import Portfolio
from app.models.trade import Trade
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioGreeksRequest,
    PortfolioGreeksResponse,
    PortfolioGreeksSummary,
    PortfolioRead,
    PortfolioUpdate,
    TradeGreeksDetail,
)
from app.services.greeks_service import greeks_service

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioRead])
def list_portfolios(
    session: Session = Depends(get_session),
) -> list[PortfolioRead]:
    """List all portfolios with trade counts."""
    portfolios = session.exec(select(Portfolio)).all()
    result: list[PortfolioRead] = []
    for p in portfolios:
        count = session.exec(
            select(func.count(Trade.id)).where(Trade.portfolio_id == p.id)
        ).one()
        result.append(
            PortfolioRead(
                id=p.id,
                name=p.name,
                description=p.description,
                trade_count=count,
            )
        )
    return result


@router.post("", response_model=PortfolioRead, status_code=201)
def create_portfolio(
    data: PortfolioCreate,
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """Create a new portfolio."""
    existing = session.exec(
        select(Portfolio).where(Portfolio.name == data.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Portfolio with this name already exists")

    portfolio = Portfolio(name=data.name, description=data.description)
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)
    return PortfolioRead(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        trade_count=0,
    )


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """Get a single portfolio."""
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    count = session.exec(
        select(func.count(Trade.id)).where(Trade.portfolio_id == portfolio.id)
    ).one()
    return PortfolioRead(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        trade_count=count,
    )


@router.put("/{portfolio_id}", response_model=PortfolioRead)
def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """Update a portfolio."""
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(portfolio, key, value)

    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)

    count = session.exec(
        select(func.count(Trade.id)).where(Trade.portfolio_id == portfolio.id)
    ).one()
    return PortfolioRead(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        trade_count=count,
    )


@router.delete("/{portfolio_id}")
def delete_portfolio(
    portfolio_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete a portfolio (rejects if it has trades)."""
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    count = session.exec(
        select(func.count(Trade.id)).where(Trade.portfolio_id == portfolio_id)
    ).one()
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete portfolio with {count} trades. Reassign or delete trades first.",
        )

    session.delete(portfolio)
    session.commit()
    return {"status": "deleted", "portfolio_id": str(portfolio_id)}


@router.post("/{portfolio_id}/greeks", response_model=PortfolioGreeksResponse)
def calculate_portfolio_greeks(
    portfolio_id: int,
    request: PortfolioGreeksRequest,
    session: Session = Depends(get_session),
) -> PortfolioGreeksResponse:
    """Calculate aggregated Greeks (Delta, Gamma) for all trades in a portfolio using QuantLib."""
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trades = session.exec(
        select(Trade).where(Trade.portfolio_id == portfolio_id)
    ).all()

    if not trades:
        return PortfolioGreeksResponse(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            trade_count=0,
            rf_rate_base=request.rf_rate_base,
            rf_rate_quote=request.rf_rate_quote,
        )

    valuation_date = request.valuation_date or date.today()

    total_delta = 0.0
    total_gamma = 0.0
    total_npv = 0.0
    trade_details: list[TradeGreeksDetail] = []

    for trade in trades:
        # Skip trades missing required fields
        if not all([trade.strike, trade.expiry_date, trade.trade_type, trade.direction]):
            trade_details.append(TradeGreeksDetail(
                trade_id=trade.id,
                trade_id_str=trade.trade_id,
                ccy_pair=trade.ccy_pair,
                option_type=trade.trade_type,
                direction=trade.direction,
                strike=trade.strike,
                notional1=trade.notional1,
                error="Missing required fields (strike, expiry_date, trade_type, direction)",
            ))
            continue

        spot = request.spot or trade.spot_rate or 6.8
        vol = request.volatility or trade.volatility or 0.05

        days_to_expiry = (trade.expiry_date - valuation_date).days
        tte = max(days_to_expiry / 365.0, 0.001)

        greeks = greeks_service.calculate_vanilla_greeks(
            option_type=trade.trade_type,
            direction=trade.direction,
            spot=spot,
            strike=float(trade.strike),
            volatility=vol,
            time_to_expiry_years=tte,
            rf_rate_base=request.rf_rate_base,
            rf_rate_quote=request.rf_rate_quote,
        )

        if greeks.get("error"):
            trade_details.append(TradeGreeksDetail(
                trade_id=trade.id,
                trade_id_str=trade.trade_id,
                ccy_pair=trade.ccy_pair,
                option_type=trade.trade_type,
                direction=trade.direction,
                strike=trade.strike,
                notional1=trade.notional1,
                error=greeks["error"],
            ))
            continue

        delta = greeks.get("delta") or 0.0
        gamma = greeks.get("gamma") or 0.0
        npv = greeks.get("npv") or 0.0

        # Weight by notional if available
        notional = trade.notional1 or 1.0
        weighted_delta = delta * notional
        weighted_gamma = gamma * notional
        weighted_npv = npv * notional

        total_delta += weighted_delta
        total_gamma += weighted_gamma
        total_npv += weighted_npv

        trade_details.append(TradeGreeksDetail(
            trade_id=trade.id,
            trade_id_str=trade.trade_id,
            ccy_pair=trade.ccy_pair,
            option_type=trade.trade_type,
            direction=trade.direction,
            strike=trade.strike,
            notional1=trade.notional1,
            delta=round(delta, 6),
            gamma=round(gamma, 6),
            npv=round(npv, 6),
        ))

    return PortfolioGreeksResponse(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio.name,
        trade_count=len(trades),
        total_delta=round(total_delta, 6),
        total_gamma=round(total_gamma, 6),
        total_npv=round(total_npv, 6),
        rf_rate_base=request.rf_rate_base,
        rf_rate_quote=request.rf_rate_quote,
        volatility_used=request.volatility,
        spot_used=request.spot,
        trades=trade_details,
    )
