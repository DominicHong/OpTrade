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
    PortfolioResolveRequest,
    PortfolioResolveResponse,
    PortfolioUpdate,
    TradeGreeksDetail,
    TradeParamsOverride,
    TradeParamsResolved,
)
from app.services.greeks_service import GreeksService
from app.services.curve_service import CurveService, get_curve_service
from app.utils.curve_helpers import extract_foreign_currency

import logging

logger = logging.getLogger("optrade.service.portfolio")


_SELL_DIRECTIONS = {"sell", "卖出"}


def _is_sell(direction: str | None) -> bool:
    """Return True if *direction* represents a short / sell position."""
    if not direction:
        return False
    return direction.lower() in _SELL_DIRECTIONS


def _resolve_premium_in_ccy2(
    premium_amount: float | None,
    premium_currency: str | None,
    ccy_pair: str | None,
    spot: float,
) -> float | None:
    """Return the premium expressed in ccy2 (the NPV quote currency).

    ``premium_amount`` is stored in ``premium_currency`` which may be either
    leg of the currency pair. NPV is denominated in ccy2 per unit of ccy1,
    so to compare premium with ``npv × notional1`` we normalise the premium
    to ccy2 using the spot rate when it is quoted in ccy1.
    """
    if premium_amount is None:
        return None

    ccy1: str | None = None
    if ccy_pair and "/" in ccy_pair:
        parts = ccy_pair.split("/")
        if len(parts) == 2:
            ccy1 = parts[0]

    if premium_currency and ccy1 and premium_currency == ccy1:
        # Premium in base currency → convert to quote currency via spot
        return premium_amount * spot
    return premium_amount


class PortfolioService:
    """Portfolio-level operations and risk aggregation service."""

    def __init__(
        self,
        greeks_service: GreeksService,
        curve_service: CurveService | None = None,
    ) -> None:
        self.greeks_service = greeks_service
        self._curve_service = curve_service

    @property
    def curve_service(self) -> CurveService:
        if self._curve_service is None:
            self._curve_service = CurveService()
        return self._curve_service

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

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
        portfolios = session.exec(select(Portfolio)).all()
        return [self._to_read(session, p) for p in portfolios]

    def get_portfolio(self, session: Session, portfolio_id: int) -> PortfolioRead:
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return self._to_read(session, portfolio)

    def create_portfolio(self, session: Session, data: PortfolioCreate) -> PortfolioRead:
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

    # ------------------------------------------------------------------
    # Curve parameter resolution
    # ------------------------------------------------------------------

    def resolve_portfolio_params(
        self,
        session: Session,
        portfolio_id: int,
        request: PortfolioResolveRequest,
    ) -> PortfolioResolveResponse:
        """Resolve curve parameters for every trade in a portfolio."""
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        trades = session.exec(
            select(Trade).where(Trade.portfolio_id == portfolio_id)
        ).all()

        resolved_trades: list[TradeParamsResolved] = []
        valuation_date = request.valuation_date

        for trade in trades:
            base: TradeParamsResolved = TradeParamsResolved(
                trade_id=trade.id,
                trade_id_str=trade.trade_id,
                ccy_pair=trade.ccy_pair,
                option_type=trade.trade_type,
                direction=trade.direction,
                strike=float(trade.strike) if trade.strike else None,
                notional1=trade.notional1,
                expiry_date=trade.expiry_date,
            )

            # Skip trades that don't have the minimum required fields
            if not trade.ccy_pair or not trade.expiry_date:
                resolved_trades.append(base)
                continue

            # Try to extract foreign currency (returns None if quote ≠ CNY)
            try:
                foreign_ccy = extract_foreign_currency(trade.ccy_pair)
            except ValueError:
                foreign_ccy = None

            if foreign_ccy is None:
                resolved_trades.append(base)
                continue

            # Compute remaining maturity
            days_to_expiry = (trade.expiry_date - valuation_date).days
            remaining_years = max(days_to_expiry / 365.0, 0.001)

            # Resolve from curve
            result = self.curve_service.resolve_valuation_params(
                session, valuation_date, foreign_ccy, remaining_years,
            )

            if result:
                base.rf_rate_base = result["rf_rate_base"]
                base.rf_rate_quote = result["rf_rate_quote"]
                base.spot = result["spot_rate"]
                base.volatility = result["volatility"]
                base.curve_resolved = True
                base.curve_date = result["curve_date"]
                base.remaining_maturity_years = round(remaining_years, 6)

            resolved_trades.append(base)

        return PortfolioResolveResponse(
            valuation_date=valuation_date,
            curve_type=request.curve_type,
            trades=resolved_trades,
        )

    # ------------------------------------------------------------------
    # Greeks calculation
    # ------------------------------------------------------------------

    def _resolve_params_for_trade(
        self,
        session: Session,
        trade: Trade,
        valuation_date: date,
        override: TradeParamsOverride | None,
        curve_type: str | None,
        curve_valuation_date: date | None,
    ) -> tuple[float, float, float, float, date | None]:
        """Resolve (spot, vol, rf_base, rf_quote, curve_date) for a single trade.

        Priority chain per field (highest first):
          1. User override from *override* (if not None)
          2. Curve resolution (if *curve_type* is set and data exists)
          3. Trade defaults → hardcoded defaults
        """
        # Start with the hardcoded / trade defaults
        spot: float = trade.spot_rate or 6.8
        vol: float = trade.volatility or 0.05
        rf_base: float = 0.03
        rf_quote: float = 0.03
        resolved_curve_date: date | None = curve_valuation_date

        # --- Curve resolution ---
        if curve_type == "fx_implied_rate":
            try:
                foreign_ccy = extract_foreign_currency(trade.ccy_pair or "")
            except ValueError:
                foreign_ccy = None

            if foreign_ccy is not None and trade.expiry_date:
                days = (trade.expiry_date - valuation_date).days
                remaining_years = max(days / 365.0, 0.001)

                result = self.curve_service.resolve_valuation_params(
                    session, valuation_date, foreign_ccy, remaining_years,
                )
                if result:
                    # Curve-derived values override the defaults
                    if result.get("rf_rate_base") is not None:
                        rf_base = result["rf_rate_base"]
                    if result.get("rf_rate_quote") is not None:
                        rf_quote = result["rf_rate_quote"]
                    if result.get("spot_rate") is not None:
                        spot = result["spot_rate"]
                    if result.get("volatility") is not None:
                        vol = result["volatility"]
                    resolved_curve_date = result.get("curve_date")

        # --- User overrides (always take priority) ---
        if override is not None:
            if override.rf_rate_base is not None:
                rf_base = override.rf_rate_base
            if override.rf_rate_quote is not None:
                rf_quote = override.rf_rate_quote
            if override.spot is not None:
                spot = override.spot
            if override.volatility is not None:
                vol = override.volatility

        return (spot, vol, rf_base, rf_quote, resolved_curve_date)

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

        # Build override lookup
        override_map: dict[int, TradeParamsOverride] = {}
        for tp in request.trade_params:
            override_map[tp.trade_id] = tp

        if not trades:
            return PortfolioGreeksResponse(
                portfolio_id=portfolio_id,
                portfolio_name=portfolio.name,
                trade_count=0,
                curve_type=request.curve_type,
            )

        valuation_date = request.valuation_date or date.today()
        curve_valuation_date: date | None = None
        total_delta = 0.0
        total_gamma = 0.0
        total_npv = 0.0
        total_profit = 0.0
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

            override = override_map.get(trade.id)
            spot, vol, rf_base, rf_quote, cd = self._resolve_params_for_trade(
                session, trade, valuation_date, override, request.curve_type, curve_valuation_date,
            )
            if cd is not None:
                curve_valuation_date = cd

            # Pass explicit dates to greeks_service — avoids TTE roundtrip
            # precision loss and lets the service handle expiry centrally
            # (expired options return all-zero Greeks).
            greeks = self.greeks_service.calculate_vanilla_greeks(
                option_type=trade.trade_type,
                direction=trade.direction,
                spot=spot,
                strike=float(trade.strike),
                volatility=vol,
                rf_rate_base=rf_base,
                rf_rate_quote=rf_quote,
                valuation_date=valuation_date,
                expiry_date=trade.expiry_date,
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

            # Premium (normalised to ccy2) and trade-level profit, expressed
            # in NPV's per-unit (ccy2 / 1 ccy1) so they are directly
            # comparable to the NPV column.
            # NPV from QuantLib is signed (positive for long, negative for
            # short). The user-facing formula uses the theoretical option
            # price (always positive): Buy profit = NPV - premium,
            # Sell profit = premium - NPV. Using the signed NPV this is
            # equivalent to:
            #   Buy  : profit_per_unit = npv - premium_per_unit
            #   Sell : profit_per_unit = premium_per_unit + npv  (npv<0)
            premium_total_ccy2 = _resolve_premium_in_ccy2(
                trade.premium_amount, trade.premium_currency, trade.ccy_pair, spot,
            )
            if premium_total_ccy2 is not None:
                premium_per_unit = premium_total_ccy2 / notional
                if _is_sell(trade.direction):
                    profit_per_unit = premium_per_unit + npv
                else:
                    profit_per_unit = npv - premium_per_unit
            else:
                premium_per_unit = None
                profit_per_unit = None

            total_delta += delta * notional
            total_gamma += gamma * notional
            total_npv += npv * notional
            if profit_per_unit is not None:
                total_profit += profit_per_unit * notional

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
                    premium=round(premium_per_unit, 6) if premium_per_unit is not None else None,
                    profit=round(profit_per_unit, 6) if profit_per_unit is not None else None,
                )
            )

        # Representative params for the response — use the first trade's resolved values
        rep_rf_base = override_map.get(
            trades[0].id,
            TradeParamsOverride(trade_id=trades[0].id),
        ).rf_rate_base
        rep_rf_quote = override_map.get(
            trades[0].id,
            TradeParamsOverride(trade_id=trades[0].id),
        ).rf_rate_quote
        rep_spot = override_map.get(
            trades[0].id,
            TradeParamsOverride(trade_id=trades[0].id),
        ).spot
        rep_vol = override_map.get(
            trades[0].id,
            TradeParamsOverride(trade_id=trades[0].id),
        ).volatility

        return PortfolioGreeksResponse(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            trade_count=len(trades),
            total_delta=round(total_delta, 6),
            total_gamma=round(total_gamma, 6),
            total_npv=round(total_npv, 6),
            total_profit=round(total_profit, 2),
            rf_rate_base=rep_rf_base,
            rf_rate_quote=rep_rf_quote,
            volatility_used=rep_vol,
            spot_used=rep_spot,
            curve_type=request.curve_type,
            curve_valuation_date=curve_valuation_date,
            trades=trade_details,
        )


def get_portfolio_service() -> PortfolioService:
    """FastAPI dependency: provide a PortfolioService instance."""
    return PortfolioService(
        greeks_service=GreeksService(),
        curve_service=CurveService(),
    )
