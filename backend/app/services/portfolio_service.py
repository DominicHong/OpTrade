"""Portfolio Service — portfolio-level operations and risk aggregation."""

from datetime import date

from fastapi import Depends, HTTPException
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Portfolio, OptionTrade, SpotTrade, SwapTrade
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
from app.services.exchange_rate_service import (
    ExchangeRateService,
    get_exchange_rate_service,
)
from app.utils.ccy_utils import split_ccy_pair
from app.utils.currency_pairs import CNY_QUOTED_PAIRS, SUPPORTED_CCY_PAIRS
from app.utils.curve_helpers import extract_foreign_currency
from app.utils.valuation_params import build_missing_params_error

import logging

logger = logging.getLogger("optrade.service.portfolio")


_SELL_DIRECTIONS = {"sell", "卖出"}


def _is_sell(direction: str | None) -> bool:
    """Return True if *direction* represents a short / sell position."""
    if not direction:
        return False
    return direction.lower() in _SELL_DIRECTIONS


def _split_ccy_pair(ccy_pair: str | None) -> tuple[str | None, str | None]:
    """Split ``"USD/CNY"`` -> ``("USD", "CNY")`` (uppercased).  Returns ``(None, None)`` if invalid."""
    base, quote = split_ccy_pair(ccy_pair)
    if base is None or quote is None:
        return None, None
    return base.upper(), quote.upper()


def _resolve_premium_in_ccy2(
    premium_amount: float | None,
    premium_currency: str | None,
    ccy_pair: str | None,
    spot: float | None,
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
    if ccy_pair:
        ccy1, _ = split_ccy_pair(ccy_pair)

    if premium_currency and ccy1 and premium_currency == ccy1:
        # Premium in base currency → convert to quote currency via spot.
        # If spot is unavailable, the conversion is impossible → None.
        if spot is None:
            return None
        return premium_amount * spot
    return premium_amount


def _missing_valuation_params(
    spot: float | None,
    vol: float | None,
    rf_base: float | None,
    rf_quote: float | None,
) -> str | None:
    """Return an error message listing missing valuation parameters, or None
    if all four are present. Used to reject live options that cannot be
    valued because the curve did not resolve a parameter and the user
    supplied no override."""
    return build_missing_params_error([
        (spot, "即期汇率"),
        (vol, "波动率"),
        (rf_base, "Base利率"),
        (rf_quote, "Quote利率"),
    ])


class PortfolioService:
    """Portfolio-level operations and risk aggregation service."""

    def __init__(
        self,
        greeks_service: GreeksService,
        curve_service: CurveService | None = None,
        exchange_rate_service: ExchangeRateService | None = None,
    ) -> None:
        self.greeks_service = greeks_service
        self._curve_service = curve_service
        self._exchange_rate_service = exchange_rate_service

    @property
    def curve_service(self) -> CurveService:
        if self._curve_service is None:
            self._curve_service = CurveService()
        return self._curve_service

    @property
    def exchange_rate_service(self) -> ExchangeRateService:
        if self._exchange_rate_service is None:
            self._exchange_rate_service = ExchangeRateService()
        return self._exchange_rate_service

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
        swap_count = session.exec(
            select(func.count(SwapTrade.id)).where(SwapTrade.portfolio_id == portfolio_id)
        ).one()
        return opt_count + spot_count + swap_count

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

        valuation_date = request.valuation_date

        # Only include options that have not yet expired as of the valuation
        # date — expired options need no valuation.
        option_trades = session.exec(
            select(OptionTrade).where(
                OptionTrade.portfolio_id == portfolio_id,
                OptionTrade.expiry_date > valuation_date,
            )
        ).all()

        resolved_trades: list[OptionTradeParamsResolved] = []

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
    ) -> tuple[float | None, float | None, float | None, float | None, date | None]:
        """Resolve (spot, vol, rf_base, rf_quote, curve_date) for a single option trade.

        Priority chain per field (highest first):
          1. User override from *override* (if not None)
          2. Curve resolution (if *curve_type* is set and data exists)
          3. None.

        A parameter that cannot be resolved stays ``None``; callers must
        handle ``None`` (e.g. report a clear error to the user) rather than
        silently substituting a default value.

        For CNY-quoted pairs (USD/CNY, EUR/CNY, etc.), curve resolution uses
        the FX implied rate curve directly.  For cross pairs (EUR/USD, etc.),
        the spot rate is read from ``ExchangeRateService`` and the two risk-
        free rates are pulled from each leg's CNY-quoted curve.  Volatility
        for cross pairs is NOT derivable from the CNY-implied curve and must
        be supplied by the user via an override.
        """
        # A parameter stays None unless the curve (or a user override) provides it.
        spot: float | None = None
        vol: float | None = None
        rf_base: float | None = None
        rf_quote: float | None = None
        resolved_curve_date: date | None = curve_valuation_date

        ccy_pair = (trade.ccy_pair or "").upper()
        base_ccy, quote_ccy = _split_ccy_pair(ccy_pair)
        is_cny_quoted = ccy_pair in CNY_QUOTED_PAIRS

        # --- Curve resolution ---
        if curve_type == "fx_implied_rate":
            if is_cny_quoted and base_ccy is not None:
                # Existing path: CNY-quoted pair → single curve lookup
                if trade.expiry_date:
                    days = (trade.expiry_date - valuation_date).days
                    remaining_years = max(days / 365.0, 0.001)

                    result = self.curve_service.resolve_valuation_params(
                        session, valuation_date, base_ccy, remaining_years,
                    )
                    if result:
                        if result.get("rf_rate_base") is not None:
                            rf_base = result["rf_rate_base"]
                        if result.get("rf_rate_quote") is not None:
                            rf_quote = result["rf_rate_quote"]
                        if result.get("spot_rate") is not None:
                            spot = result["spot_rate"]
                        if result.get("volatility") is not None:
                            vol = result["volatility"]
                        resolved_curve_date = result.get("curve_date")

            elif base_ccy is not None and quote_ccy is not None:
                # Cross pair (EUR/USD, USD/HKD, ...) — decompose into two
                # CNY-quoted curve lookups + exchange_rate spot.
                er_spot = self.exchange_rate_service.get_rate(
                    session, ccy_pair, valuation_date,
                )
                if er_spot is not None:
                    spot = er_spot

                if trade.expiry_date:
                    days = (trade.expiry_date - valuation_date).days
                    remaining_years = max(days / 365.0, 0.001)

                    # rf_rate_base ← base_ccy/CNY curve's foreign_implied_rate
                    base_result = self.curve_service.resolve_valuation_params(
                        session, valuation_date, base_ccy, remaining_years,
                    )
                    if base_result:
                        if base_result.get("rf_rate_base") is not None:
                            rf_base = base_result["rf_rate_base"]
                        if resolved_curve_date is None:
                            resolved_curve_date = base_result.get("curve_date")

                    # rf_rate_quote ← quote_ccy/CNY curve's foreign_implied_rate
                    # (skip if quote is CNY — already set to CNY rate above)
                    if quote_ccy != "CNY":
                        quote_result = self.curve_service.resolve_valuation_params(
                            session, valuation_date, quote_ccy, remaining_years,
                        )
                        if quote_result:
                            if quote_result.get("rf_rate_base") is not None:
                                rf_quote = quote_result["rf_rate_base"]
                            if resolved_curve_date is None:
                                resolved_curve_date = quote_result.get("curve_date")
                    else:
                        # quote is CNY → use CNY risk-free rate from base curve
                        if base_result and base_result.get("rf_rate_quote") is not None:
                            rf_quote = base_result["rf_rate_quote"]

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

            # Live options require all four market-data params; an option at
            # or past expiry returns zero Greeks regardless, so params are not
            # required for it (its P&L comes from exercise, not valuation).
            if valuation_date <= trade.expiry_date:
                missing = _missing_valuation_params(spot, vol, rf_base, rf_quote)
                if missing:
                    trade_details.append(
                        OptionTradeGreeksDetail(
                            trade_id=trade.id,
                            trade_id_str=trade.trade_id,
                            ccy_pair=trade.ccy_pair,
                            option_type=trade.trade_type,
                            direction=trade.direction,
                            strike=trade.strike,
                            notional1=trade.notional1,
                            error=missing,
                        )
                    )
                    continue

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
        """Return the earliest trade_date across option, spot & swap trades in given portfolios."""

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
        min_swap = session.exec(
            select(func.min(SwapTrade.trade_date)).where(
                SwapTrade.portfolio_id.in_(portfolio_ids),
            )
        ).one()

        candidates: list[date] = [d for d in (min_option, min_spot, min_swap) if d is not None]
        return min(candidates) if candidates else None

    def _empty_aggregated_response(
        self,
        request: "AggregatedAnalysisRequest",
        valuation_date: date,
    ) -> "AggregatedAnalysisResponse":
        """Return a zero-filled response when no trades exist."""
        from app.schemas.portfolio import (
            AggregatedAnalysisResponse,
            AggregatedSummary,
        )

        is_multi = len(request.portfolio_ids) > 1
        display_name = "多投组" if is_multi else ""
        TARGET_CURRENCIES = {"CNY", "USD", "HKD", "EUR", "JPY", "GBP"}

        return AggregatedAnalysisResponse(
            portfolio_name=display_name,
            portfolio_count=len(request.portfolio_ids),
            option_trade_count=0,
            spot_trade_count=0,
            swap_trade_count=0,
            start_date=request.start_date,
            valuation_date=valuation_date,
            curve_type=request.curve_type,
            curve_valuation_date=valuation_date,
            summary=AggregatedSummary(
                option_metrics_by_ccy_pair=[],
                total_option_pnl_cny=0.0,
                total_spot_pnl_cny=0.0,
                total_swap_pnl_cny=0.0,
                total_pnl_cny=0.0,
                currency_exposures={c: 0.0 for c in TARGET_CURRENCIES},
            ),
            option_trades=[],
            spot_trades=[],
            swap_trades=[],
        )

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
        if not ccy_pair or "/" not in ccy_pair:
            return None, f"Invalid currency pair: {ccy_pair!r}"

        if ccy_pair.upper() not in SUPPORTED_CCY_PAIRS:
            return None, f"Unsupported currency pair: {ccy_pair}"

        ccy_pair_upper = ccy_pair.upper()
        if ccy_pair_upper in CNY_QUOTED_PAIRS:
            # CNY-quoted pair → use FX implied rate curve
            foreign_ccy = split_ccy_pair(ccy_pair_upper)[0]
            market_rate = self.curve_service.get_spot_rate_for_date(
                session, valuation_date, foreign_ccy,
            )
            if market_rate is None:
                return None, f"No curve data for {foreign_ccy} at {valuation_date}"
            return market_rate, None

        # Cross pair (USD/HKD, EUR/USD, ...) → use ExchangeRateService
        market_rate = self.exchange_rate_service.get_rate(
            session, ccy_pair_upper, valuation_date,
        )
        if market_rate is None:
            return None, f"No exchange rate for {ccy_pair_upper} at {valuation_date}"
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
        ccy_pair_upper = (ccy_pair or "").upper()
        if not ccy_pair_upper or "/" not in ccy_pair_upper:
            return None

        if ccy_pair_upper in CNY_QUOTED_PAIRS:
            foreign_ccy = split_ccy_pair(ccy_pair_upper)[0]
            return self.curve_service.get_spot_rate_for_date(
                session, expiry_date, foreign_ccy,
            )

        # Cross pair
        return self.exchange_rate_service.get_rate(
            session, ccy_pair_upper, expiry_date,
        )

    def _process_spot_trade(
        self,
        session: Session,
        trade,
        valuation_date: date,
        curve_type: str | None,
        is_derivative: bool,
        expiry_spot_rate: float | None,
        *,
        start_date: date | None = None,
    ) -> "SpotTradeAnalysisDetail":
        """Process a single spot trade for P&L calculation.

        When ``trade_date < start_date``, the position pre-dates the P&L
        interval.  The ``adjusted_deal_price`` is then set to the market
        rate at ``start_date`` so that P&L reflects only the
        ``[start_date, valuation_date]`` window.
        """
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
        if start_date is not None and trade.trade_date is not None and trade.trade_date < start_date:
            start_rate, start_err = self._resolve_spot_params(
                session, trade.ccy_pair, start_date, curve_type,
            )
            if start_err or start_rate is None:
                detail.error = f"Cannot resolve market rate at start_date {start_date}: {start_err}"
                return detail
            adjusted_deal = start_rate
        elif is_derivative and expiry_spot_rate is not None:
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

    def _process_swap_trade(
        self,
        trade,
        valuation_date: date,
        *,
        start_date: date | None = None,
    ) -> "SwapTradeAnalysisDetail":
        """Process a single swap trade for P&L calculation.

        P&L (in ccy2, the quote currency) is the price difference between
        the far and near leg multiplied by the near-leg ccy1 notional:

            buy  ccy1/ccy2 (Buy/Sell):  PnL = (far - near) * |notional|
            sell ccy1/ccy2 (Sell/Buy):  PnL = (near - far) * |notional|

        Accrual rule (overlap between ``[start_date, valuation_date]`` and
        ``[near_value_date, far_value_date]``):

            - valuation_date <  near_value_date  → PnL = 0  (未起息)
            - near_value_date ≤ valuation_date < far_value_date → PnL = full × overlap/total (存续)
            - valuation_date ≥ far_value_date     → PnL = full (到期)

        When ``start_date`` is provided and later than ``near_value_date``,
        only the ``[start_date, min(valuation_date, far_value_date)]``
        portion is recognised.

        Return rate (annualised, percent, 2 decimals):
            buy : (far - near) / near × 365 / total_days × 100
            sell: (near - far) / near × 365 / total_days × 100
        """
        from app.schemas.portfolio import SwapTradeAnalysisDetail

        direction = (trade.direction or "").strip()
        # Buy/Sell  → buy ccy1/ccy2 (near buy, far sell)
        # Sell/Buy  → sell ccy1/ccy2 (near sell, far buy)
        is_buy = direction.lower().startswith("buy")

        detail = SwapTradeAnalysisDetail(
            trade_id=trade.id,
            trade_id_str=trade.trade_id,
            ccy_pair=trade.ccy_pair,
            direction=trade.direction,
            near_deal_price=trade.near_deal_price,
            far_deal_price=trade.far_deal_price,
            near_value_date=trade.near_value_date,
            far_value_date=trade.far_value_date,
            notional=trade.near_ccy1_amount,
            trade_date=trade.trade_date,
        )

        if not trade.ccy_pair:
            detail.error = "Missing currency pair"
            return detail

        if (
            trade.near_deal_price is None
            or trade.far_deal_price is None
            or trade.near_value_date is None
            or trade.far_value_date is None
            or trade.near_ccy1_amount is None
        ):
            detail.error = "Missing data for P&L calculation (near/far price, value dates, or notional)"
            return detail

        near_price = float(trade.near_deal_price)
        far_price = float(trade.far_deal_price)
        notional = abs(float(trade.near_ccy1_amount))
        near_vd = trade.near_value_date
        far_vd = trade.far_value_date

        total_days = (far_vd - near_vd).days
        # Guard against non-positive horizons (malformed data / same-day legs)
        if total_days <= 0:
            total_days = 0

        # Full (maturity) PnL in ccy2
        if is_buy:
            full_pnl = (far_price - near_price) * notional
            price_diff = far_price - near_price
        else:
            full_pnl = (near_price - far_price) * notional
            price_diff = near_price - far_price

        # Status + accrual (overlap between [start_date, val_date] and [near_vd, far_vd])
        if valuation_date < near_vd:
            status = "未起息"
        elif valuation_date >= far_vd:
            status = "到期"
        else:
            status = "存续"

        if total_days > 0:
            accrual_start = max(start_date, near_vd) if start_date is not None else near_vd
            accrual_end = min(valuation_date, far_vd)
            accrued_days = max(0, (accrual_end - accrual_start).days)
            pnl = full_pnl * accrued_days / total_days
            # Clamp to [0, full_pnl] (or [full_pnl, 0] when full_pnl < 0)
            if full_pnl >= 0:
                pnl = max(0.0, min(pnl, full_pnl))
            else:
                pnl = max(full_pnl, min(pnl, 0.0))
        else:
            # Degenerate same-day legs
            pnl = full_pnl if valuation_date >= far_vd else 0.0

        detail.status = status
        # normalise -0.0 → 0.0 to avoid "-0.00" display
        pnl = 0.0 if pnl == 0 else pnl
        detail.pnl = round(pnl, 2)

        # Return rate (annualised percent, 2 decimals)
        if total_days > 0 and near_price != 0:
            return_rate = (price_diff / near_price) * 365.0 / total_days * 100.0
            detail.return_rate = round(return_rate, 2)

        return detail

    def calculate_aggregated_analysis(
        self,
        session: Session,
        request: "AggregatedAnalysisRequest",
    ) -> "AggregatedAnalysisResponse":
        """Calculate aggregated P&L across multiple portfolios.

        Queries option, spot and swap trades for the selected portfolios
        whose position exists at ``valuation_date`` (i.e. ``trade_date``
        for spot/option, ``near_value_date`` for swap, both ``<=
        valuation_date``).  The ``start_date`` does **not** filter trades
        in or out — it only adjusts the P&L formula for trades dealt
        before ``start_date`` so that only the ``[start_date,
        valuation_date]`` portion is recognised.
        """
        from app.schemas.portfolio import (
            AggregatedAnalysisRequest,
            AggregatedAnalysisResponse,
            AggregatedSummary,
            OptionTradeAnalysisDetail,
            SpotTradeAnalysisDetail,
            SwapTradeAnalysisDetail,
        )

        # --- 1. Resolve start_date ---
        start_date = request.start_date or self._find_earliest_trade_date(
            session, request.portfolio_ids,
        )
        valuation_date = request.valuation_date

        # If no trades exist in the selected portfolios, return empty result early.
        # (start_date is None when _find_earliest_trade_date finds no trades.)
        if start_date is None:
            return self._empty_aggregated_response(
                request, valuation_date,
            )

        # --- 2. Query option trades (trade_date <= val_date) ---
        # A trade is included whenever its position exists at val_date,
        # regardless of whether trade_date < start_date.  The start_date
        # only adjusts the P&L formula, not the inclusion filter.
        option_trades = session.exec(
            select(OptionTrade).where(
                OptionTrade.portfolio_id.in_(request.portfolio_ids),
                OptionTrade.trade_date <= valuation_date,
            )
        ).all()

        # --- 3. Query spot trades (trade_date <= val_date) ---
        spot_trades = session.exec(
            select(SpotTrade).where(
                SpotTrade.portfolio_id.in_(request.portfolio_ids),
                SpotTrade.trade_date <= valuation_date,
            )
        ).all()

        # Build spot trade_id → SpotTrade lookup for exercise resolution
        spot_by_trade_id: dict[str, SpotTrade] = {
            s.trade_id: s for s in spot_trades
        }

        # --- 3b. Query swap trades (near_value_date <= val_date) ---
        # Swap uses near_value_date as the reference date for inclusion:
        # a swap whose near leg hasn't been reached has zero P&L.
        swap_trades = session.exec(
            select(SwapTrade).where(
                SwapTrade.portfolio_id.in_(request.portfolio_ids),
                SwapTrade.near_value_date <= valuation_date,
            )
        ).all()

        # --- 4. Build override lookup ---
        override_map: dict[int, OptionTradeParamsOverride] = {}
        for tp in request.trade_params:
            override_map[tp.trade_id] = tp

        # --- 5. Process option trades ---
        option_details: list[OptionTradeAnalysisDetail] = []
        # Map: spot_trade DB id → expiry_spot_rate (for derivative spot adjustment)
        derivative_spot_map: dict[int, float] = {}

        # Per-currency-pair aggregation (original-currency Greeks + CNY P&L).
        # delta/gamma are kept in original ccy2/1ccy1 units; P&L items are
        # converted to CNY using the valuation-date FX rate for ccy2.
        from app.schemas.portfolio import CcyPairOptionMetrics
        per_pair: dict[str, CcyPairOptionMetrics] = {}
        # Cache FX rate lookups: ccy2 → (rate, had_error).  Avoids repeat queries.
        fx_rate_cache: dict[str, float | None] = {}

        def _get_fx_to_cny(ccy2: str) -> float | None:
            ccy2_u = ccy2.upper()
            if ccy2_u in fx_rate_cache:
                return fx_rate_cache[ccy2_u]
            rate = self.exchange_rate_service.get_rate_to_cny(session, ccy2_u, valuation_date)
            fx_rate_cache[ccy2_u] = rate
            return rate

        def _get_or_create_pair_metrics(ccy_pair: str) -> CcyPairOptionMetrics | None:
            ccy_pair_u = ccy_pair.upper()
            if ccy_pair_u not in per_pair:
                _, quote_ccy = _split_ccy_pair(ccy_pair_u)
                if quote_ccy is None:
                    return None
                fx_rate = _get_fx_to_cny(quote_ccy)
                per_pair[ccy_pair_u] = CcyPairOptionMetrics(
                    ccy_pair=ccy_pair_u,
                    fx_rate_to_cny=fx_rate,
                )
            return per_pair[ccy_pair_u]

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

            # Live options require all four market-data params; an option at
            # or past expiry returns zero Greeks regardless, so params are not
            # required for it (its P&L comes from exercise, not valuation).
            if valuation_date <= trade.expiry_date:
                missing = _missing_valuation_params(spot, vol, rf_base, rf_quote)
                if missing:
                    detail.error = missing
                    option_details.append(detail)
                    continue

            notional = trade.notional1 or 1.0

            # Premium (normalised to ccy2 per unit)
            premium_total = _resolve_premium_in_ccy2(
                trade.premium_amount, trade.premium_currency, trade.ccy_pair, spot,
            )
            premium_per_unit = (premium_total / notional) if premium_total is not None else None

            # Determine this trade's ccy2 → CNY FX rate up-front (used for
            # populating both detail-level *_cny fields and pair aggregation).
            _, trade_quote_ccy = _split_ccy_pair(trade.ccy_pair)
            trade_fx_rate = _get_fx_to_cny(trade_quote_ccy) if trade_quote_ccy else None
            detail.fx_rate_to_cny = trade_fx_rate

            # --- Compute Greeks at val_date (always needed for risk metrics) ---
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

            npv_val = greeks.get("npv") or 0.0
            detail.delta = round(greeks.get("delta") or 0.0, 6)
            detail.gamma = round(greeks.get("gamma") or 0.0, 6)
            detail.theta = round(greeks.get("theta") or 0.0, 6)
            detail.vega = round(greeks.get("vega") or 0.0, 6)
            detail.npv = round(npv_val, 6)
            detail.premium = round(premium_per_unit, 6) if premium_per_unit is not None else None

            # --- Exercise P&L (if expired and exercised) ---
            exercise_pnl: float | None = None
            if valuation_date >= trade.expiry_date:
                if trade.exercise_derivative_trade_id:
                    derivative_spot = spot_by_trade_id.get(trade.exercise_derivative_trade_id)
                    if derivative_spot is not None:
                        market_rate_at_expiry = self._resolve_expiry_spot_rate(
                            session, trade.ccy_pair or "", trade.expiry_date,
                        )
                        if market_rate_at_expiry is not None and trade.strike:
                            if trade.trade_type.upper() == "CALL":
                                exercise_value = (market_rate_at_expiry - float(trade.strike)) * notional
                            else:
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
                        detail.exercise_status = trade.exercise_status or "未行权"
                else:
                    detail.exercise_status = trade.exercise_status or "未行权"
            else:
                detail.exercise_status = trade.exercise_status or "未到期"

            # --- P&L mode: interval (trade_date < start_date) vs original ---
            pre_interval = (
                start_date is not None
                and trade.trade_date is not None
                and trade.trade_date < start_date
            )

            if pre_interval:
                # Interval P&L: premium excluded, P&L = value(val) - value(start)
                if trade.expiry_date <= start_date:
                    # Expired before interval — no interval P&L from option
                    detail.premium_pnl = 0.0
                    detail.exercise_pnl = 0.0
                else:
                    # Option alive at start_date — compute NPV(start_date).
                    # Pass the user override so user-supplied params (e.g.
                    # cross-pair volatility, which the curve cannot derive)
                    # also apply at start_date; curve-resolvable fields are
                    # still taken from the start_date curve when the override
                    # leaves them None.
                    spot_s, vol_s, rfb_s, rfq_s, _ = self._resolve_params_for_trade(
                        session, trade, start_date, override, request.curve_type, None,
                    )
                    greeks_start = self.greeks_service.calculate_vanilla_greeks(
                        option_type=trade.trade_type,
                        direction=trade.direction,
                        spot=spot_s,
                        strike=float(trade.strike),
                        volatility=vol_s,
                        rf_rate_base=rfb_s,
                        rf_rate_quote=rfq_s,
                        valuation_date=start_date,
                        expiry_date=trade.expiry_date,
                    )
                    if greeks_start.get("error"):
                        detail.error = greeks_start["error"]
                        option_details.append(detail)
                        continue

                    npv_start = greeks_start.get("npv") or 0.0
                    detail.premium_pnl = round((npv_val - npv_start) * notional, 2)
                    detail.exercise_pnl = round(exercise_pnl, 2) if exercise_pnl is not None else None

                if detail.premium_pnl is not None and detail.exercise_pnl is not None:
                    detail.total_pnl = round(detail.premium_pnl + detail.exercise_pnl, 2)
                elif detail.premium_pnl is not None:
                    detail.total_pnl = detail.premium_pnl
            else:
                # Original algorithm (start_date <= trade_date)
                if valuation_date < trade.expiry_date:
                    if premium_per_unit is not None:
                        if _is_sell(trade.direction):
                            profit_per_unit = premium_per_unit + npv_val
                        else:
                            profit_per_unit = npv_val - premium_per_unit
                        detail.premium_pnl = round(profit_per_unit * notional, 2)
                    detail.exercise_pnl = None
                    detail.total_pnl = detail.premium_pnl
                else:
                    if premium_per_unit is not None:
                        if _is_sell(trade.direction):
                            detail.premium_pnl = round((premium_per_unit + npv_val) * notional, 2)
                        else:
                            detail.premium_pnl = round((npv_val - premium_per_unit) * notional, 2)
                    detail.exercise_pnl = round(exercise_pnl, 2) if exercise_pnl is not None else None
                    if detail.premium_pnl is not None:
                        detail.total_pnl = round(detail.premium_pnl + (exercise_pnl or 0.0), 2)

            # --- CNY conversion for detail-level mirror fields ---
            if trade_fx_rate is not None:
                if detail.npv is not None:
                    detail.npv_cny = round(detail.npv * notional * trade_fx_rate, 2)
                if detail.premium_pnl is not None:
                    detail.premium_pnl_cny = round(detail.premium_pnl * trade_fx_rate, 2)
                if detail.exercise_pnl is not None:
                    detail.exercise_pnl_cny = round(detail.exercise_pnl * trade_fx_rate, 2)
                if detail.total_pnl is not None:
                    detail.total_pnl_cny = round(detail.total_pnl * trade_fx_rate, 2)

            # --- Per-currency-pair aggregation ---
            pair_metrics = _get_or_create_pair_metrics(trade.ccy_pair or "")
            if pair_metrics is not None:
                pair_metrics.trade_count += 1
                if detail.delta is not None:
                    pair_metrics.delta += detail.delta * notional
                if detail.gamma is not None:
                    pair_metrics.gamma += detail.gamma * notional
                if detail.theta is not None:
                    pair_metrics.theta += detail.theta * notional
                if detail.vega is not None:
                    pair_metrics.vega += detail.vega * notional
                # NPV / P&L aggregated in CNY (sum of *_cny values)
                if detail.npv_cny is not None:
                    pair_metrics.npv_cny += detail.npv_cny
                if detail.premium_pnl_cny is not None:
                    pair_metrics.premium_pnl_cny += detail.premium_pnl_cny
                if detail.exercise_pnl_cny is not None:
                    pair_metrics.exercise_pnl_cny += detail.exercise_pnl_cny
                if detail.total_pnl_cny is not None:
                    pair_metrics.total_option_pnl_cny += detail.total_pnl_cny

            option_details.append(detail)

        # --- 6. Process spot trades ---
        spot_details: list[SpotTradeAnalysisDetail] = []
        total_spot_pnl_cny = 0.0

        for trade in spot_trades:
            is_derivative = trade.id in derivative_spot_map
            expiry_spot = derivative_spot_map.get(trade.id)
            detail = self._process_spot_trade(
                session, trade, valuation_date, request.curve_type,
                is_derivative, expiry_spot, start_date=start_date,
            )

            # CNY conversion for spot P&L
            _, spot_quote_ccy = _split_ccy_pair(trade.ccy_pair)
            if spot_quote_ccy and detail.pnl is not None and detail.error is None:
                spot_fx = _get_fx_to_cny(spot_quote_ccy)
                detail.fx_rate_to_cny = spot_fx
                if spot_fx is not None:
                    detail.pnl_cny = round(detail.pnl * spot_fx, 2)
                    total_spot_pnl_cny += detail.pnl_cny

            spot_details.append(detail)

        # --- 6b. Process swap trades ---
        swap_details: list[SwapTradeAnalysisDetail] = []
        total_swap_pnl_cny = 0.0

        for trade in swap_trades:
            detail = self._process_swap_trade(trade, valuation_date, start_date=start_date)

            # CNY conversion for swap P&L (pnl is in ccy2)
            _, swap_quote_ccy = _split_ccy_pair(trade.ccy_pair)
            if swap_quote_ccy and detail.pnl is not None and detail.error is None:
                swap_fx = _get_fx_to_cny(swap_quote_ccy)
                detail.fx_rate_to_cny = swap_fx
                if swap_fx is not None:
                    detail.pnl_cny = round(detail.pnl * swap_fx, 2)
                    total_swap_pnl_cny += detail.pnl_cny

            swap_details.append(detail)

        # --- Currency exposure (spot trades only) ---
        TARGET_CURRENCIES = {"CNY", "USD", "HKD", "EUR", "JPY", "GBP"}
        currency_exposures: dict[str, float] = {c: 0.0 for c in TARGET_CURRENCIES}

        for trade in spot_trades:
            ccy1 = (trade.ccy1 or "").upper()
            ccy2 = (trade.ccy2 or "").upper()

            # Fall back to parsing from ccy_pair if ccy1/ccy2 not populated
            if (not ccy1 or not ccy2) and trade.ccy_pair:
                pair_base, pair_quote = _split_ccy_pair(trade.ccy_pair)
                if pair_base and pair_quote:
                    if not ccy1:
                        ccy1 = pair_base
                    if not ccy2:
                        ccy2 = pair_quote

            amt1 = trade.ccy1_amount or 0.0
            amt2 = trade.ccy2_amount or 0.0

            if ccy1 in TARGET_CURRENCIES:
                currency_exposures[ccy1] += amt1
            if ccy2 in TARGET_CURRENCIES:
                currency_exposures[ccy2] += amt2

        # --- 7. Finalise per-pair metrics (round + compute total_option_pnl_cny) ---
        option_metrics_list: list[CcyPairOptionMetrics] = []
        total_option_pnl_cny = 0.0
        for pair_metrics in per_pair.values():
            pair_metrics.delta = round(pair_metrics.delta, 6)
            pair_metrics.gamma = round(pair_metrics.gamma, 6)
            pair_metrics.theta = round(pair_metrics.theta, 6)
            pair_metrics.vega = round(pair_metrics.vega, 6)
            pair_metrics.npv_cny = round(pair_metrics.npv_cny, 2)
            pair_metrics.premium_pnl_cny = round(pair_metrics.premium_pnl_cny, 2)
            pair_metrics.exercise_pnl_cny = round(pair_metrics.exercise_pnl_cny, 2)
            pair_metrics.total_option_pnl_cny = round(pair_metrics.total_option_pnl_cny, 2)
            total_option_pnl_cny += pair_metrics.total_option_pnl_cny
            option_metrics_list.append(pair_metrics)

        # Sort by ccy_pair for stable display
        option_metrics_list.sort(key=lambda m: m.ccy_pair)

        total_pnl_cny = round(total_option_pnl_cny + total_spot_pnl_cny + total_swap_pnl_cny, 2)

        # --- 8. Determine portfolio_name ---
        all_names = session.exec(
            select(Portfolio.name).where(Portfolio.id.in_(request.portfolio_ids))
        ).all()
        is_multi = len(request.portfolio_ids) > 1
        display_name = "多投组" if is_multi else (all_names[0] if all_names else "")

        # --- 9. Build response ---
        summary = AggregatedSummary(
            option_metrics_by_ccy_pair=option_metrics_list,
            total_option_pnl_cny=round(total_option_pnl_cny, 2),
            total_spot_pnl_cny=round(total_spot_pnl_cny, 2),
            total_swap_pnl_cny=round(total_swap_pnl_cny, 2),
            total_pnl_cny=total_pnl_cny,
            currency_exposures=currency_exposures,
        )

        return AggregatedAnalysisResponse(
            portfolio_name=display_name,
            portfolio_count=len(request.portfolio_ids),
            option_trade_count=len(option_trades),
            spot_trade_count=len(spot_trades),
            swap_trade_count=len(swap_trades),
            start_date=start_date,
            valuation_date=valuation_date,
            curve_type=request.curve_type,
            curve_valuation_date=curve_valuation_date,
            summary=summary,
            option_trades=option_details,
            spot_trades=spot_details,
            swap_trades=swap_details,
        )


def get_portfolio_service() -> PortfolioService:
    """FastAPI dependency: provide a PortfolioService instance."""
    return PortfolioService(
        greeks_service=GreeksService(),
        curve_service=CurveService(),
        exchange_rate_service=ExchangeRateService(),
    )
