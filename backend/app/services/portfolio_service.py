"""Portfolio Service — portfolio-level operations and risk aggregation."""

from datetime import date

from fastapi import Depends, HTTPException
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Portfolio, Trade
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioGreeksRequest,
    PortfolioGreeksResponse,
    PortfolioRead,
    PortfolioUpdate,
    TradeGreeksDetail,
)
from app.services.greeks_service import GreeksService


class PortfolioService:
    """Portfolio-level operations and risk aggregation service."""

    def __init__(self, greeks_service: GreeksService) -> None:
        self.greeks_service = greeks_service

    def _trade_count(self, session: Session, portfolio_id: int) -> int:
        return session.exec(
            select(func.count(Trade.id)).where(Trade.portfolio_id == portfolio_id)
        ).one()

    def _to_read(self, session: Session, portfolio: Portfolio) -> PortfolioRead:
        return PortfolioRead(
            id=portfolio.id,
            name=portfolio.name,
            description=portfolio.description,
            trade_count=self._trade_count(session, portfolio.id),
        )

    def list_portfolios(self, session: Session) -> list[PortfolioRead]:
        """List all portfolios with trade counts."""
        portfolios = session.exec(select(Portfolio)).all()
        return [self._to_read(session, p) for p in portfolios]

    def get_portfolio(self, session: Session, portfolio_id: int) -> PortfolioRead:
        """Get a single portfolio by ID."""
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return self._to_read(session, portfolio)

    def create_portfolio(self, session: Session, data: PortfolioCreate) -> PortfolioRead:
        """Create a new portfolio."""
        existing = session.exec(
            select(Portfolio).where(Portfolio.name == data.name)
        ).first()
        if existing:
            raise HTTPException(
                status_code=409, detail="Portfolio with this name already exists"
            )

        portfolio = Portfolio(name=data.name, description=data.description)
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)
        return self._to_read(session, portfolio)

    def update_portfolio(
        self, session: Session, portfolio_id: int, data: PortfolioUpdate
    ) -> PortfolioRead:
        """Update an existing portfolio."""
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(portfolio, key, value)

        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)
        return self._to_read(session, portfolio)

    def delete_portfolio(self, session: Session, portfolio_id: int) -> None:
        """Delete a portfolio (rejects if it has trades)."""
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        count = self._trade_count(session, portfolio_id)
        if count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete portfolio with {count} trades. Reassign or delete trades first.",
            )

        session.delete(portfolio)
        session.commit()

    def calculate_greeks(
        self,
        session: Session,
        portfolio_id: int,
        request: PortfolioGreeksRequest,
    ) -> PortfolioGreeksResponse:
        """Calculate aggregated Greeks for all trades in a portfolio."""
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
            if not all([trade.strike, trade.expiry_date, trade.trade_type, trade.direction]):
                trade_details.append(
                    TradeGreeksDetail(
                        trade_id=trade.id,
                        trade_id_str=trade.trade_id,
                        ccy_pair=trade.ccy_pair,
                        option_type=trade.trade_type,
                        direction=trade.direction,
                        strike=trade.strike,
                        notional1=trade.notional1,
                        error="Missing required fields (strike, expiry_date, trade_type, direction)",
                    )
                )
                continue

            spot = request.spot or trade.spot_rate or 6.8
            vol = request.volatility or trade.volatility or 0.05
            days_to_expiry = (trade.expiry_date - valuation_date).days
            tte = max(days_to_expiry / 365.0, 0.001)

            greeks = self.greeks_service.calculate_vanilla_greeks(
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
                trade_details.append(
                    TradeGreeksDetail(
                        trade_id=trade.id,
                        trade_id_str=trade.trade_id,
                        ccy_pair=trade.ccy_pair,
                        option_type=trade.trade_type,
                        direction=trade.direction,
                        strike=trade.strike,
                        notional1=trade.notional1,
                        error=greeks["error"],
                    )
                )
                continue

            delta = greeks.get("delta") or 0.0
            gamma = greeks.get("gamma") or 0.0
            npv = greeks.get("npv") or 0.0
            notional = trade.notional1 or 1.0

            total_delta += delta * notional
            total_gamma += gamma * notional
            total_npv += npv * notional

            trade_details.append(
                TradeGreeksDetail(
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
                )
            )

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


def get_portfolio_service() -> PortfolioService:
    """FastAPI dependency: provide a PortfolioService instance."""
    return PortfolioService(greeks_service=GreeksService())
