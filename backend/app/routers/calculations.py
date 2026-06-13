from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.models.calculation import CalculationResult
from app.models.trade import Trade
from app.schemas.calculation import GreeksRequest, GreeksResult, PricingRequest, PricingResult
from app.services.greeks_service import greeks_service
from app.services.pricing_service import pricing_service

router = APIRouter(prefix="/api/v1/calculations", tags=["calculations"])


@router.post("/greeks", response_model=list[GreeksResult])
def calculate_greeks(
    request: GreeksRequest,
    session: Session = Depends(get_session),
) -> list[GreeksResult]:
    """Calculate Greeks for the given trade IDs using QuantLib."""
    results: list[GreeksResult] = []

    for trade_id in request.trade_ids:
        trade = session.get(Trade, trade_id)
        if not trade:
            results.append(GreeksResult(
                trade_id=trade_id,
                calculation_date=date.today(),
                error=f"Trade {trade_id} not found",
                scenario_label=request.scenario_label,
            ))
            continue

        if not all([trade.strike, trade.expiry_date, trade.trade_type, trade.direction]):
            results.append(GreeksResult(
                trade_id=trade_id,
                calculation_date=date.today(),
                error="Trade missing required fields (strike, expiry_date, trade_type, direction)",
                scenario_label=request.scenario_label,
            ))
            continue

        # Determine inputs
        spot = request.spot or trade.spot_rate or 6.8
        vol = request.volatility or trade.volatility or 0.05
        rate = request.risk_free_rate or 0.03

        days_to_expiry = (trade.expiry_date - date.today()).days
        tte = max(days_to_expiry / 365.0, 0.001)

        greeks = greeks_service.calculate_vanilla_greeks(
            option_type=trade.trade_type,
            direction=trade.direction,
            spot=spot,
            strike=float(trade.strike),
            volatility=vol,
            time_to_expiry_years=tte,
            risk_free_rate_domestic=rate,
        )

        # Persist to cache
        result_record = CalculationResult(
            trade_id=trade.id,
            calculation_date=date.today(),
            spot=spot,
            volatility=vol,
            risk_free_rate=rate,
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
            risk_free_rate=rate,
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
        risk_free_rate_domestic=request.risk_free_rate,
        notional=request.notional,
    )
    return PricingResult(
        npv=result.get("npv"),
        fair_premium=result.get("fair_premium"),
        currency=result.get("currency", "base"),
        error=result.get("error"),
    )
