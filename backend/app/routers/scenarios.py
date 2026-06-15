from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.services.scenario_service import scenario_service

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


@router.post("/spot-shift")
def scenario_spot_shift(
    request: dict,
    session: Session = Depends(get_session),
) -> list[dict]:
    """Shift spot rate by given amounts and recalculate Greeks."""
    shifts = request.get("shifts_bps", None)
    return scenario_service.spot_shift(
        option_type=request.get("option_type", "Call"),
        direction=request.get("direction", "Buy"),
        base_spot=request.get("base_spot", 6.8),
        strike=request.get("strike", 6.8),
        base_vol=request.get("base_vol", 0.05),
        time_to_expiry_years=request.get("time_to_expiry_years", 1.0),
        rf_rate_base=request.get("rf_rate_base", 0.03),
        rf_rate_quote=request.get("rf_rate_quote", 0.03),
        shifts_bps=shifts,
    )


@router.post("/vol-shift")
def scenario_vol_shift(
    request: dict,
    session: Session = Depends(get_session),
) -> list[dict]:
    """Shift volatility by given amounts and recalculate Greeks."""
    shifts = request.get("shifts_vol", None)
    return scenario_service.vol_shift(
        option_type=request.get("option_type", "Call"),
        direction=request.get("direction", "Buy"),
        spot=request.get("spot", 6.8),
        strike=request.get("strike", 6.8),
        base_vol=request.get("base_vol", 0.05),
        time_to_expiry_years=request.get("time_to_expiry_years", 1.0),
        rf_rate_base=request.get("rf_rate_base", 0.03),
        rf_rate_quote=request.get("rf_rate_quote", 0.03),
        shifts_vol=shifts,
    )


@router.post("/time-decay")
def scenario_time_decay(
    request: dict,
    session: Session = Depends(get_session),
) -> list[dict]:
    """Calculate Greeks at future dates (time decay profile)."""
    days = request.get("days_forward", None)
    return scenario_service.time_decay(
        option_type=request.get("option_type", "Call"),
        direction=request.get("direction", "Buy"),
        spot=request.get("spot", 6.8),
        strike=request.get("strike", 6.8),
        volatility=request.get("volatility", 0.05),
        time_to_expiry_years=request.get("time_to_expiry_years", 1.0),
        rf_rate_base=request.get("rf_rate_base", 0.03),
        rf_rate_quote=request.get("rf_rate_quote", 0.03),
        days_forward=days,
    )


@router.post("/heatmap")
def scenario_heatmap(
    request: dict,
    session: Session = Depends(get_session),
) -> dict:
    """Generate 2D spot x vol heatmap data."""
    valuation_date_str = request.get("valuation_date")
    valuation_date = date.fromisoformat(valuation_date_str) if valuation_date_str else date.today()

    # If valuation_date is provided, adjust time_to_expiry_years
    base_tte = request.get("time_to_expiry_years", 1.0)
    # No expiry_date in current request, so we just pass tte through
    # (portfolio-level heatmap will handle this differently in Phase 4)

    return scenario_service.heatmap(
        option_type=request.get("option_type", "Call"),
        direction=request.get("direction", "Buy"),
        base_spot=request.get("base_spot", 6.8),
        strike=request.get("strike", 6.8),
        base_vol=request.get("base_vol", 0.05),
        time_to_expiry_years=base_tte,
        rf_rate_base=request.get("rf_rate_base", 0.03),
        rf_rate_quote=request.get("rf_rate_quote", 0.03),
        spot_shifts=request.get("spot_shifts"),
        vol_shifts=request.get("vol_shifts"),
    )
