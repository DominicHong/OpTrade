"""Scenarios router — scenario analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas.scenario import (
    BuiltinScenariosRequest,
    BuiltinScenariosResponse,
    DefaultPairParams,
    EarliestTradeDateResponse,
    RequiredPairsResponse,
    ScenarioAnalysisRequest,
    ScenarioAnalysisResponse,
    ScenarioSweepRequest,
    ScenarioSweepResponse,
)
from app.services.scenario_service import scenario_service

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


@router.get("/required-pairs", response_model=RequiredPairsResponse)
def get_required_pairs(
    portfolio_ids: str | None = None,
    valuation_date: str | None = None,
    session: Session = Depends(get_session),
) -> RequiredPairsResponse:
    """Return the set of currency pairs needed for scenario analysis."""
    from datetime import date as date_cls

    ids: list[int] | None = None
    if portfolio_ids and portfolio_ids.strip():
        try:
            ids = [int(x.strip()) for x in portfolio_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid portfolio_ids format")

    val_date: date_cls
    if valuation_date:
        val_date = date_cls.fromisoformat(valuation_date)
    else:
        val_date = date_cls.today()

    return scenario_service.extract_required_pairs(session, ids, val_date)


@router.get("/default-pair-params", response_model=DefaultPairParams)
def get_default_pair_params(
    ccy_pair: str,
    valuation_date: str,
    curve_type: str | None = None,
    session: Session = Depends(get_session),
) -> DefaultPairParams:
    """Return default valuation params for a currency pair."""
    from datetime import date as date_cls

    return scenario_service.resolve_default_pair_params(
        session, ccy_pair, date_cls.fromisoformat(valuation_date), curve_type,
    )


@router.get("/earliest-trade-date", response_model=EarliestTradeDateResponse)
def get_earliest_trade_date(
    session: Session = Depends(get_session),
) -> EarliestTradeDateResponse:
    """Return the global earliest trade date across all portfolios."""
    return scenario_service.earliest_trade_date(session)


@router.post("/analyze", response_model=ScenarioAnalysisResponse)
def analyze_scenario(
    request: ScenarioAnalysisRequest,
    session: Session = Depends(get_session),
) -> ScenarioAnalysisResponse:
    """Run a single scenario analysis with per-pair overrides."""
    return scenario_service.analyze_custom_scenario(
        session, request,
        scenario_id=request.pair_overrides and "custom" or None,
        scenario_name=request.pair_overrides and "自定义情景" or None,
    )


@router.post("/builtin", response_model=BuiltinScenariosResponse)
def analyze_builtin_scenarios(
    request: BuiltinScenariosRequest,
    session: Session = Depends(get_session),
) -> BuiltinScenariosResponse:
    """Run all builtin scenarios and return results including baseline."""
    return scenario_service.analyze_builtin_scenarios(session, request)


@router.post("/sweep", response_model=ScenarioSweepResponse)
def analyze_sweep(
    request: ScenarioSweepRequest,
    session: Session = Depends(get_session),
) -> ScenarioSweepResponse:
    """Sweep one variable across a range for a single currency pair."""
    return scenario_service.analyze_sweep(session, request)
