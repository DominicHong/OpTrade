"""Portfolio Service — portfolio-level operations and risk aggregation."""

from datetime import date

from fastapi import Depends, HTTPException
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Portfolio, OptionTrade, SpotTrade
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioGreeksRequest,
    PortfolioGreeksResponse,
    PortfolioRead,
    PortfolioResolveRequest,
    PortfolioResolveResponse,
    PortfolioUpdate,
    OptionTradeGreeksDetail,
    OptionTradeParamsOverride,
    OptionTradeParamsResolved,
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
        opt_count = session.exec(
            select(func.count(OptionTrade.id)).where(OptionTrade.portfolio_id == portfolio_id)
        ).one()
        spot_count = session.exec(
            select(func.count(SpotTrade.id)).where(SpotTrade.portfolio_id == portfolio_id)
        ).one()
        return opt_count + spot_count

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
        """Resolve curve parameters for every option trade in a portfolio."""
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        option_trades = session.exec(
            select(OptionTrade).where(OptionTrade.portfolio_id == portfolio_id)
        ).all()

        resolved_trades: list[OptionTradeParamsResolved] = []
        valuation_date = request.valuation_date

        for trade in option_trades:
            base: OptionTradeParamsResolved = OptionTradeParamsResolved(
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
        trade: OptionTrade,
        valuation_date: date,
        override: OptionTradeParamsOverride | None,
        curve_type: str | None,
        curve_valuation_date: date | None,
    ) -> tuple[float, float, float, float, date | None]:
        """Resolve (spot, vol, rf_base, rf_quote, curve_date) for a single option trade.

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
        """Calculate aggregated Greeks for all option trades in a portfolio."""
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        option_trades = session.exec(
            select(OptionTrade).where(OptionTrade.portfolio_id == portfolio_id)
        ).all()

        # Build override lookup
        override_map: dict[int, OptionTradeParamsOverride] = {}
        for tp in request.trade_params:
            override_map[tp.trade_id] = tp

        if not option_trades:
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
        trade_details: list[OptionTradeGreeksDetail] = []

        for trade in option_trades:
            if not all([trade.strike, trade.expiry_date, trade.trade_type, trade.direction]):
                trade_details.append(
                    OptionTradeGreeksDetail(
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
                    OptionTradeGreeksDetail(
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
                OptionTradeGreeksDetail(
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
            option_trades[0].id,
            OptionTradeParamsOverride(trade_id=option_trades[0].id),
        ).rf_rate_base
        rep_rf_quote = override_map.get(
            option_trades[0].id,
            OptionTradeParamsOverride(trade_id=option_trades[0].id),
        ).rf_rate_quote
        rep_spot = override_map.get(
            option_trades[0].id,
            OptionTradeParamsOverride(trade_id=option_trades[0].id),
        ).spot
        rep_vol = override_map.get(
            option_trades[0].id,
            OptionTradeParamsOverride(trade_id=option_trades[0].id),
        ).volatility

        return PortfolioGreeksResponse(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            trade_count=len(option_trades),
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


    # ------------------------------------------------------------------
    # Multi-portfolio aggregated P&L analysis
    # ------------------------------------------------------------------

    def _find_earliest_trade_date(
        self, session: Session, portfolio_ids: list[int],
    ) -> date | None:
        """Return the earliest trade_date across option & spot trades in given portfolios."""

        min_option = session.exec(
            select(func.min(OptionTrade.trade_date)).where(
                OptionTrade.portfolio_id.in_(portfolio_ids),
            )
        ).one()
        min_spot = session.exec(
            select(func.min(SpotTrade.trade_date)).where(
                SpotTrade.portfolio_id.in_(portfolio_ids),
            )
        ).one()

        candidates: list[date] = [d for d in (min_option, min_spot) if d is not None]
        return min(candidates) if candidates else None

    def _resolve_spot_params(
        self,
        session: Session,
        ccy_pair: str,
        valuation_date: date,
        curve_type: str | None,
    ) -> tuple[float | None, str | None]:
        """Resolve market rate for a spot trade's currency pair.

        Returns:
            ``(market_rate, error)`` — exactly one is non-None.
        """
        from app.schemas.portfolio import SUPPORTED_CCY_PAIRS
        from app.utils.curve_helpers import extract_foreign_currency

        if not ccy_pair or "/" not in ccy_pair:
            return None, f"Invalid currency pair: {ccy_pair!r}"

        if ccy_pair.upper() not in SUPPORTED_CCY_PAIRS:
            return None, f"Unsupported currency pair: {ccy_pair}"

        try:
            foreign_ccy = extract_foreign_currency(ccy_pair)
        except ValueError as e:
            return None, str(e)

        if foreign_ccy is None:
            return None, f"Quote currency is not CNY: {ccy_pair}"

        market_rate = self.curve_service.get_spot_rate_for_date(
            session, valuation_date, foreign_ccy,
        )
        if market_rate is None:
            return None, f"No curve data for {foreign_ccy} at {valuation_date}"

        return market_rate, None

    def _resolve_expiry_spot_rate(
        self,
        session: Session,
        ccy_pair: str,
        expiry_date: date,
    ) -> float | None:
        """Get the market spot rate at an option's expiry date.

        Returns ``None`` when no curve data is available.
        """
        from app.utils.curve_helpers import extract_foreign_currency

        try:
            foreign_ccy = extract_foreign_currency(ccy_pair)
        except ValueError:
            return None
        if foreign_ccy is None:
            return None

        return self.curve_service.get_spot_rate_for_date(
            session, expiry_date, foreign_ccy,
        )

    def _process_spot_trade(
        self,
        session: Session,
        trade,
        valuation_date: date,
        curve_type: str | None,
        is_derivative: bool,
        expiry_spot_rate: float | None,
    ) -> "SpotTradeAnalysisDetail":
        """Process a single spot trade for P&L calculation."""
        from app.schemas.portfolio import SpotTradeAnalysisDetail

        detail = SpotTradeAnalysisDetail(
            trade_id=trade.id,
            trade_id_str=trade.trade_id,
            ccy_pair=trade.ccy_pair,
            direction=trade.direction,
            deal_price=trade.deal_price,
            notional=trade.ccy1_amount,
            trade_date=trade.trade_date,
            settlement_date=trade.settlement_date,
            is_derivative=is_derivative,
        )

        if not trade.ccy_pair:
            detail.error = "Missing currency pair"
            return detail

        market_rate, error = self._resolve_spot_params(
            session, trade.ccy_pair, valuation_date, curve_type,
        )
        if error:
            detail.error = error
            return detail

        detail.market_rate = market_rate

        # Determine adjusted deal price
        if is_derivative and expiry_spot_rate is not None:
            adjusted_deal = expiry_spot_rate
        else:
            adjusted_deal = trade.deal_price

        detail.adjusted_deal_price = adjusted_deal

        if adjusted_deal is None or market_rate is None or trade.ccy1_amount is None:
            detail.error = "Missing data for P&L calculation (deal_price, market_rate, or notional)"
            return detail

        # P&L = (market_rate - adjusted_deal_price) * notional
        # ccy1_amount already carries direction sign (positive=long, negative=short)
        pnl = (market_rate - adjusted_deal) * trade.ccy1_amount
        detail.pnl = round(pnl, 2)

        return detail

    def calculate_aggregated_analysis(
        self,
        session: Session,
        request: "AggregatedAnalysisRequest",
    ) -> "AggregatedAnalysisResponse":
        """Calculate aggregated P&L across multiple portfolios.

        Queries option and spot trades for the selected portfolios whose
        ``trade_date`` falls between ``start_date`` and ``valuation_date``,
        then computes per-trade P&L with the new exercise-aware option
        algorithm and standard spot P&L algorithm.
        """
        from app.schemas.portfolio import (
            AggregatedAnalysisRequest,
            AggregatedAnalysisResponse,
            AggregatedSummary,
            OptionTradeAnalysisDetail,
            SpotTradeAnalysisDetail,
        )

        # --- 1. Resolve start_date ---
        start_date = request.start_date or self._find_earliest_trade_date(
            session, request.portfolio_ids,
        )
        valuation_date = request.valuation_date

        # --- 2. Query option trades in date range ---
        option_trades = session.exec(
            select(OptionTrade).where(
                OptionTrade.portfolio_id.in_(request.portfolio_ids),
                OptionTrade.trade_date >= start_date,
                OptionTrade.trade_date <= valuation_date,
            )
        ).all()

        # --- 3. Query spot trades in date range ---
        spot_trades = session.exec(
            select(SpotTrade).where(
                SpotTrade.portfolio_id.in_(request.portfolio_ids),
                SpotTrade.trade_date >= start_date,
                SpotTrade.trade_date <= valuation_date,
            )
        ).all()

        # Build spot trade_id → SpotTrade lookup for exercise resolution
        spot_by_trade_id: dict[str, SpotTrade] = {
            s.trade_id: s for s in spot_trades
        }

        # --- 4. Build override lookup ---
        override_map: dict[int, OptionTradeParamsOverride] = {}
        for tp in request.trade_params:
            override_map[tp.trade_id] = tp

        # --- 5. Process option trades ---
        option_details: list[OptionTradeAnalysisDetail] = []
        # Map: spot_trade DB id → expiry_spot_rate (for derivative spot adjustment)
        derivative_spot_map: dict[int, float] = {}

        total_delta = 0.0
        total_gamma = 0.0
        total_npv = 0.0
        total_premium_pnl = 0.0
        total_exercise_pnl = 0.0
        curve_valuation_date: date | None = None

        for trade in option_trades:
            detail = OptionTradeAnalysisDetail(
                trade_id=trade.id,
                trade_id_str=trade.trade_id,
                ccy_pair=trade.ccy_pair,
                option_type=trade.trade_type,
                direction=trade.direction,
                strike=trade.strike,
                notional1=trade.notional1,
                trade_date=trade.trade_date,
                expiry_date=trade.expiry_date,
                exercise_status=trade.exercise_status,
            )

            # Validate required fields
            if not all([trade.strike, trade.expiry_date, trade.trade_type, trade.direction]):
                detail.error = "Missing required fields (strike, expiry_date, trade_type, direction)"
                option_details.append(detail)
                continue

            # Resolve spot/vol/rates
            override = override_map.get(trade.id)
            spot, vol, rf_base, rf_quote, cd = self._resolve_params_for_trade(
                session, trade, valuation_date, override, request.curve_type, None,
            )
            if cd is not None:
                curve_valuation_date = cd

            notional = trade.notional1 or 1.0

            # Premium (normalised to ccy2 per unit)
            premium_total = _resolve_premium_in_ccy2(
                trade.premium_amount, trade.premium_currency, trade.ccy_pair, spot,
            )
            premium_per_unit = (premium_total / notional) if premium_total is not None else None

            if valuation_date < trade.expiry_date:
                # --- PRE-EXPIRY: unchanged from existing logic ---
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
                    detail.error = greeks["error"]
                    option_details.append(detail)
                    continue

                npv = greeks.get("npv") or 0.0

                if premium_per_unit is not None:
                    if _is_sell(trade.direction):
                        profit_per_unit = premium_per_unit + npv
                    else:
                        profit_per_unit = npv - premium_per_unit
                else:
                    profit_per_unit = None

                detail.delta = round(greeks.get("delta") or 0.0, 6)
                detail.gamma = round(greeks.get("gamma") or 0.0, 6)
                detail.npv = round(npv, 6)
                detail.premium = round(premium_per_unit, 6) if premium_per_unit is not None else None
                detail.premium_pnl = round(profit_per_unit * notional, 2) if profit_per_unit is not None else None
                detail.exercise_pnl = None
                detail.total_pnl = detail.premium_pnl

                if detail.delta:
                    total_delta += detail.delta * notional
                if detail.gamma:
                    total_gamma += detail.gamma * notional
                if detail.npv is not None:
                    total_npv += detail.npv * notional
                if detail.premium_pnl is not None:
                    total_premium_pnl += detail.premium_pnl

            else:
                # --- EXPIRED / AT-EXPIRY PATH ---
                # NPV = 0 for expired options (QuantLib returns zeros)
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

                npv = greeks.get("npv") or 0.0
                detail.delta = round(greeks.get("delta") or 0.0, 6)
                detail.gamma = round(greeks.get("gamma") or 0.0, 6)
                detail.npv = round(npv, 6)
                detail.premium = round(premium_per_unit, 6) if premium_per_unit is not None else None

                # Premium P&L (with NPV=0 for expired), multiplied by notional for total display
                if premium_per_unit is not None:
                    if _is_sell(trade.direction):
                        detail.premium_pnl = round((premium_per_unit + npv) * notional, 2)
                    else:
                        detail.premium_pnl = round((npv - premium_per_unit) * notional, 2)

                # Exercise check
                exercise_pnl: float | None = None
                if trade.exercise_derivative_trade_id:
                    derivative_spot = spot_by_trade_id.get(trade.exercise_derivative_trade_id)
                    if derivative_spot is not None:
                        # Option was exercised — compute exercise P&L
                        market_rate_at_expiry = self._resolve_expiry_spot_rate(
                            session, trade.ccy_pair or "", trade.expiry_date,
                        )
                        if market_rate_at_expiry is not None and trade.strike:
                            if trade.trade_type.upper() == "CALL":
                                exercise_value = (market_rate_at_expiry - float(trade.strike)) * notional
                            else:  # PUT
                                exercise_value = (float(trade.strike) - market_rate_at_expiry) * notional

                            if _is_sell(trade.direction):
                                exercise_value = -exercise_value

                            exercise_pnl = exercise_value
                            derivative_spot_map[derivative_spot.id] = market_rate_at_expiry
                            detail.exercise_status = "已行权"
                        else:
                            exercise_pnl = 0.0
                            detail.exercise_status = "已行权"
                    else:
                        # exercise_derivative_trade_id set but spot not in date range
                        detail.exercise_status = trade.exercise_status or "未行权"
                else:
                    # No exercise_derivative_trade_id → not exercised
                    detail.exercise_status = trade.exercise_status or "未行权"

                detail.exercise_pnl = round(exercise_pnl, 2) if exercise_pnl is not None else None

                # Total option P&L = premium_pnl + exercise_pnl (both already total amounts)
                if detail.premium_pnl is not None:
                    total_pnl_val = detail.premium_pnl + (exercise_pnl or 0.0)
                    detail.total_pnl = round(total_pnl_val, 2)

                # Aggregate (detail values are already totals)
                if detail.delta:
                    total_delta += detail.delta * notional
                if detail.gamma:
                    total_gamma += detail.gamma * notional
                if detail.npv is not None:
                    total_npv += detail.npv * notional
                if detail.premium_pnl is not None:
                    total_premium_pnl += detail.premium_pnl
                if exercise_pnl is not None:
                    total_exercise_pnl += exercise_pnl

            option_details.append(detail)

        # --- 6. Process spot trades ---
        spot_details: list[SpotTradeAnalysisDetail] = []
        total_spot_pnl = 0.0

        for trade in spot_trades:
            is_derivative = trade.id in derivative_spot_map
            expiry_spot = derivative_spot_map.get(trade.id)
            detail = self._process_spot_trade(
                session, trade, valuation_date, request.curve_type,
                is_derivative, expiry_spot,
            )
            spot_details.append(detail)
            if detail.pnl is not None and detail.error is None:
                total_spot_pnl += detail.pnl

        # --- Currency exposure (spot trades only) ---
        TARGET_CURRENCIES = {"CNY", "USD", "HKD", "EUR", "JPY", "GBP"}
        currency_exposures: dict[str, float] = {c: 0.0 for c in TARGET_CURRENCIES}

        for trade in spot_trades:
            ccy1 = (trade.ccy1 or "").upper()
            ccy2 = (trade.ccy2 or "").upper()

            # Fall back to parsing from ccy_pair if ccy1/ccy2 not populated
            if (not ccy1 or not ccy2) and trade.ccy_pair and "/" in trade.ccy_pair:
                parts = trade.ccy_pair.upper().split("/")
                if len(parts) == 2:
                    if not ccy1:
                        ccy1 = parts[0]
                    if not ccy2:
                        ccy2 = parts[1]

            amt1 = trade.ccy1_amount or 0.0
            amt2 = trade.ccy2_amount or 0.0

            if ccy1 in TARGET_CURRENCIES:
                currency_exposures[ccy1] += amt1
            if ccy2 in TARGET_CURRENCIES:
                currency_exposures[ccy2] += amt2

        # --- 7. Determine portfolio_name ---
        all_names = session.exec(
            select(Portfolio.name).where(Portfolio.id.in_(request.portfolio_ids))
        ).all()
        is_multi = len(request.portfolio_ids) > 1
        display_name = "多投组" if is_multi else (all_names[0] if all_names else "")

        # --- 8. Build response ---
        summary = AggregatedSummary(
            total_delta=round(total_delta, 6),
            total_gamma=round(total_gamma, 6),
            total_npv=round(total_npv, 6),
            total_option_premium_pnl=round(total_premium_pnl, 2),
            total_option_exercise_pnl=round(total_exercise_pnl, 2),
            total_option_pnl=round(total_premium_pnl + total_exercise_pnl, 2),
            total_spot_pnl=round(total_spot_pnl, 2),
            total_pnl=round(total_premium_pnl + total_exercise_pnl + total_spot_pnl, 2),
            currency_exposures=currency_exposures,
        )

        return AggregatedAnalysisResponse(
            portfolio_name=display_name,
            portfolio_count=len(request.portfolio_ids),
            option_trade_count=len(option_trades),
            spot_trade_count=len(spot_trades),
            start_date=start_date,
            valuation_date=valuation_date,
            curve_type=request.curve_type,
            curve_valuation_date=curve_valuation_date,
            summary=summary,
            option_trades=option_details,
            spot_trades=spot_details,
        )


def get_portfolio_service() -> PortfolioService:
    """FastAPI dependency: provide a PortfolioService instance."""
    return PortfolioService(
        greeks_service=GreeksService(),
        curve_service=CurveService(),
    )
