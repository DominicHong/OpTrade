from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.models import CalculationResult, OptionTrade
from app.schemas.calculation import GreeksRequest, GreeksResult, PricingRequest, PricingResult
from app.services.greeks_service import greeks_service
from app.services.pricing_service import pricing_service

router = APIRouter(prefix="/api/v1/calculations", tags=["calculations"])


@router.post("/greeks", response_model=list[GreeksResult])
def calculate_greeks(
    request: GreeksRequest,
    session: Session = Depends(get_session),
) -> list[GreeksResult]:
    """Calculate Greeks for the given option trade IDs using QuantLib."""
    results: list[GreeksResult] = []

    for trade_id in request.trade_ids:
        trade = session.get(OptionTrade, trade_id)
        if not trade:
            results.append(GreeksResult(
                trade_id=trade_id,
                calculation_date=date.today(),
                error=f"OptionTrade {trade_id} not found",
                scenario_label=request.scenario_label,
            ))
            continue

        if not all([trade.strike, trade.expiry_date, trade.trade_type, trade.direction]):
            results.append(GreeksResult(
                trade_id=trade_id,
                calculation_date=date.today(),
                error="Option trade missing required fields (strike, expiry_date, trade_type, direction)",
                scenario_label=request.scenario_label,
            ))
            continue

        # Determine inputs
        spot = request.spot or trade.spot_rate or 6.8
        vol = request.volatility or trade.volatility or 0.05
        rf_rate_base = request.rf_rate_base or 0.03
        rf_rate_quote = request.rf_rate_quote or 0.03

        valuation_date = request.valuation_date or date.today()
        days_to_expiry = (trade.expiry_date - valuation_date).days
        tte = max(days_to_expiry / 365.0, 0.001)

        greeks = greeks_service.calculate_vanilla_greeks(
            option_type=trade.trade_type,
            direction=trade.direction,
            spot=spot,
            strike=float(trade.strike),
            volatility=vol,
            rf_rate_base=rf_rate_base,
            rf_rate_quote=rf_rate_quote,
            valuation_date=valuation_date,
            expiry_date=trade.expiry_date,
        )

        # Persist to cache
        result_record = CalculationResult(
            trade_id=trade.id,
            calculation_date=date.today(),
            spot=spot,
            volatility=vol,
            rf_rate_base=rf_rate_base,
            rf_rate_quote=rf_rate_quote,
            time_to_expiry_years=tte,
            npv=greeks.get("npv"),
            delta=greeks.get("delta"),
            gamma=greeks.get("gamma"),
            vega=greeks.get("vega"),
            theta=greeks.get("theta"),
            rho=greeks.get("rho"),
            scenario_label=request.scenario_label,
        )
        session.add(result_record)

        results.append(GreeksResult(
            trade_id=trade.id,
            calculation_date=date.today(),
            npv=greeks.get("npv"),
            delta=greeks.get("delta"),
            gamma=greeks.get("gamma"),
            vega=greeks.get("vega"),
            theta=greeks.get("theta"),
            rho=greeks.get("rho"),
            spot=spot,
            volatility=vol,
            rf_rate_base=rf_rate_base,
            rf_rate_quote=rf_rate_quote,
            time_to_expiry_years=tte,
            scenario_label=request.scenario_label,
            error=greeks.get("error"),
        ))

    session.commit()
    return results


@router.post("/price", response_model=PricingResult)
def price_option(request: PricingRequest) -> PricingResult:
    """Ad-hoc pricing for given option parameters."""
    result = pricing_service.price_vanilla(
        option_type=request.option_type,
        direction=request.direction,
        spot=request.spot,
        strike=request.strike,
        volatility=request.volatility,
        time_to_expiry_years=request.time_to_expiry_years,
        rf_rate_base=request.rf_rate_base,
        rf_rate_quote=request.rf_rate_quote,
        notional=request.notional,
    )
    return PricingResult(
        npv=result.get("npv"),
        fair_premium=result.get("fair_premium"),
        currency=result.get("currency", "base"),
        error=result.get("error"),
    )
