"""Scenario Analysis schemas — request/response models for the scenario analysis API."""

from datetime import date
from pydantic import BaseModel

from app.schemas.portfolio import (
    AggregatedAnalysisResponse,
    AggregatedSummary,
    CcyPairOptionMetrics,
)


# ---------------------------------------------------------------------------
# Core request / response
# ---------------------------------------------------------------------------


class CcyPairScenarioOverride(BaseModel):
    """Per-currency-pair scenario override (absolute values, not shocks)."""

    ccy_pair: str
    spot: float | None = None
    volatility: float | None = None
    rf_rate_base: float | None = None
    rf_rate_quote: float | None = None


class ScenarioAnalysisRequest(BaseModel):
    """Request for a single scenario analysis (custom or builtin)."""

    portfolio_ids: list[int] | None = None
    start_date: date | None = None
    valuation_date: date
    curve_type: str | None = None
    pair_overrides: list[CcyPairScenarioOverride] = []


class ScenarioAnalysisResponse(AggregatedAnalysisResponse):
    """Response for a single scenario analysis run."""

    scenario_id: str | None = None
    scenario_name: str | None = None


class BuiltinScenariosRequest(BaseModel):
    """Request to run all builtin scenarios in one shot."""

    portfolio_ids: list[int] | None = None
    start_date: date | None = None
    valuation_date: date
    curve_type: str | None = None


class BuiltinScenariosResponse(BaseModel):
    """Response containing all builtin scenario results plus the baseline."""

    baseline: ScenarioAnalysisResponse
    scenarios: list[ScenarioAnalysisResponse]


# ---------------------------------------------------------------------------
# Supporting endpoints
# ---------------------------------------------------------------------------


class RequiredPairsResponse(BaseModel):
    """The set of currency pairs needed to model all live positions."""
    option_pairs: list[str]
    spot_pairs: list[str]
    swap_pairs: list[str]
    derived_ccy_to_cny_pairs: list[str]
    all_pairs: list[str]


class DefaultPairParams(BaseModel):
    """Default valuation parameters for one currency pair."""
    ccy_pair: str
    spot: float | None = None
    volatility: float | None = None
    rf_rate_base: float | None = None
    rf_rate_quote: float | None = None
    curve_date: date | None = None


class EarliestTradeDateResponse(BaseModel):
    """Global earliest trade date across all portfolios."""
    earliest_trade_date: date | None = None


# ---------------------------------------------------------------------------
# Sweep analysis
# ---------------------------------------------------------------------------


class ScenarioSweepRequest(BaseModel):
    """Sweep one variable across a range for a single currency pair."""

    portfolio_ids: list[int] | None = None
    start_date: date | None = None
    valuation_date: date
    curve_type: str | None = None
    ccy_pair: str
    variable: str  # "spot" | "volatility" | "rf_rate_base" | "rf_rate_quote"
    min_value: float
    max_value: float
    num_steps: int = 20


class SweepStepResult(BaseModel):
    """Summary-level result at one sweep step."""

    variable_value: float
    summary: AggregatedSummary


class ScenarioSweepResponse(BaseModel):
    """Response for a variable sweep analysis."""

    ccy_pair: str
    variable: str
    sweep_points: list[float]
    results: list[SweepStepResult]
