"""Scenario Service — scenario analysis engine.

Computes per-currency-pair scenario results by expanding pair-level
overrides into trade-level overrides and reusing the existing
PortfolioService.calculate_aggregated_analysis pipeline.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import date

from sqlmodel import Session, select

from app.models import OptionTrade, Portfolio, SpotTrade, SwapTrade
from app.schemas.portfolio import AggregatedAnalysisRequest, OptionTradeParamsOverride
from app.schemas.scenario import (
    BuiltinScenariosRequest,
    BuiltinScenariosResponse,
    CcyPairScenarioOverride,
    DefaultPairParams,
    EarliestTradeDateResponse,
    RequiredPairsResponse,
    ScenarioAnalysisRequest,
    ScenarioAnalysisResponse,
)
from app.services.curve_service import CurveService, get_curve_service
from app.services.exchange_rate_service import (
    ExchangeRateService,
    get_exchange_rate_service,
)
from app.services.greeks_service import GreeksService
from app.services.portfolio_service import PortfolioService
from app.utils.ccy_utils import split_ccy_pair
from app.utils.currency_pairs import CNY_QUOTED_PAIRS, SUPPORTED_CCY_PAIRS

logger = logging.getLogger("optrade.service.scenario")

_REPRESENTATIVE_MATURITY_YEARS = 0.25


# ── builtin scenario definitions ──────────────────────────────────────

def _build_builtin_scenarios() -> list[tuple[str, str, ...]]:
    """Return (id, name, is_vol_rel, vol_factor, is_spot_rel, spot_factor)."""
    return [
        ("base",        "基准情景",                              False, 1.0,  False, 1.0),
        ("vol_up_10",   "波动率上升 +10%",                        True,  1.10, False, 1.0),
        ("vol_up_20",   "波动率上升 +20%",                        True,  1.20, False, 1.0),
        ("vol_dn_10",   "波动率下降 -10%",                        True,  0.90, False, 1.0),
        ("vol_dn_20",   "波动率下降 -20%",                        True,  0.80, False, 1.0),
        ("spot_up_1",   "即期升值 +1%",                          False, 1.0,  True,  1.01),
        ("spot_up_5",   "即期升值 +5%",                          False, 1.0,  True,  1.05),
        ("spot_dn_1",   "即期贬值 -1%",                          False, 1.0,  True,  0.99),
        ("spot_dn_5",   "即期贬值 -5%",                          False, 1.0,  True,  0.95),
        ("vol_up_sp_dn","波动率+20% & 即期-5% (风险逆转)",         True,  1.20, True,  0.95),
        ("vol_up_sp_up","波动率+20% & 即期+5% (正冲击)",           True,  1.20, True,  1.05),
    ]


BUILTIN_SCENARIOS = _build_builtin_scenarios()


# ── helpers ───────────────────────────────────────────────────────────


def _split_ccy(ccy_pair: str | None) -> tuple[str | None, str | None]:
    base, quote = split_ccy_pair(ccy_pair)
    if base is None or quote is None:
        return None, None
    return base.upper(), quote.upper()


def _all_portfolio_ids(session: Session) -> list[int]:
    rows = session.exec(select(Portfolio.id)).all()
    return list(rows)


def _global_earliest_trade_date(session: Session) -> date | None:
    from sqlmodel import func as sql_func

    dates: list[date | None] = []

    opt_min = session.exec(
        select(sql_func.min(OptionTrade.trade_date))
    ).first()
    if opt_min:
        dates.append(opt_min)

    spot_min = session.exec(
        select(sql_func.min(SpotTrade.trade_date))
    ).first()
    if spot_min:
        dates.append(spot_min)

    swap_min = session.exec(
        select(sql_func.min(SwapTrade.trade_date))
    ).first()
    if swap_min:
        dates.append(swap_min)

    return min(dates) if dates else None


# ── ScenarioService ───────────────────────────────────────────────────


class ScenarioService:
    """Scenario analysis engine."""

    def __init__(
        self,
        greeks_service: GreeksService | None = None,
        curve_service: CurveService | None = None,
        exchange_rate_service: ExchangeRateService | None = None,
    ) -> None:
        self.greeks_service = greeks_service or GreeksService()
        self.curve_service = curve_service or CurveService()
        self.exchange_rate_service = exchange_rate_service or ExchangeRateService()
        self._portfolio_service = PortfolioService(
            greeks_service=self.greeks_service,
            curve_service=self.curve_service,
            exchange_rate_service=self.exchange_rate_service,
        )

    # ── pair extraction ───────────────────────────────────────────

    def extract_required_pairs(
        self,
        session: Session,
        portfolio_ids: list[int] | None,
        valuation_date: date,
    ) -> RequiredPairsResponse:
        """Determine all currency pairs needed to model live positions."""
        if portfolio_ids is None:
            portfolio_ids = _all_portfolio_ids(session)

        if not portfolio_ids:
            return RequiredPairsResponse(
                option_pairs=[], spot_pairs=[], swap_pairs=[],
                derived_ccy_to_cny_pairs=[], all_pairs=[],
            )

        option_pairs: set[str] = set()
        spot_pairs: set[str] = set()
        swap_pairs: set[str] = set()

        # Option: live (expiry > val_date) or at expiry
        option_rows = session.exec(
            select(OptionTrade.ccy_pair).where(
                OptionTrade.portfolio_id.in_(portfolio_ids),
                OptionTrade.trade_date <= valuation_date,
            )
        ).all()
        for ccy_pair in option_rows:
            if isinstance(ccy_pair, tuple):
                ccy_pair = ccy_pair[0]
            if ccy_pair:
                option_pairs.add(ccy_pair.upper())

        # Spot: all positions at valuation_date
        spot_rows = session.exec(
            select(SpotTrade.ccy_pair, SpotTrade.ccy1, SpotTrade.ccy2,
                   SpotTrade.ccy1_amount, SpotTrade.ccy2_amount).where(
                SpotTrade.portfolio_id.in_(portfolio_ids),
                SpotTrade.trade_date <= valuation_date,
            )
        ).all()

        for ccy_pair, ccy1, ccy2, amt1, amt2 in spot_rows:
            if ccy_pair:
                spot_pairs.add(ccy_pair.upper())

        # Swap: live (far_value_date > val_date)
        swap_rows = session.exec(
            select(SwapTrade.ccy_pair).where(
                SwapTrade.portfolio_id.in_(portfolio_ids),
                SwapTrade.far_value_date > valuation_date,
            )
        ).all()
        for ccy_pair in swap_rows:
            if isinstance(ccy_pair, tuple):
                ccy_pair = ccy_pair[0]
            if ccy_pair:
                swap_pairs.add(ccy_pair.upper())

        # Derive XXX/CNY pairs from spot non-CNY exposures
        derived_ccy_to_cny: set[str] = set()
        spot_ccy_exposures: set[str] = set()
        for _ccy_pair, ccy1, ccy2, amt1, amt2 in spot_rows:
            for ccy, amt in [(ccy1, amt1), (ccy2, amt2)]:
                if ccy and amt and ccy.upper() != "CNY":
                    spot_ccy_exposures.add(ccy.upper())

        for ccy in spot_ccy_exposures:
            pair = f"{ccy}/CNY"
            if pair in SUPPORTED_CCY_PAIRS:
                derived_ccy_to_cny.add(pair)

        all_pairs = sorted((option_pairs | spot_pairs | swap_pairs | derived_ccy_to_cny))

        return RequiredPairsResponse(
            option_pairs=sorted(option_pairs),
            spot_pairs=sorted(spot_pairs),
            swap_pairs=sorted(swap_pairs),
            derived_ccy_to_cny_pairs=sorted(derived_ccy_to_cny),
            all_pairs=all_pairs,
        )

    # ── default pair params ────────────────────────────────────────

    def resolve_default_pair_params(
        self,
        session: Session,
        ccy_pair: str,
        valuation_date: date,
        curve_type: str | None = None,
    ) -> DefaultPairParams:
        """Resolve default valuation params for a single currency pair."""
        ccy_pair_upper = ccy_pair.upper()
        base, quote = _split_ccy(ccy_pair_upper)

        spot: float | None = None
        vol: float | None = None
        rf_base: float | None = None
        rf_quote: float | None = None
        curve_date: date | None = None

        if base is None or quote is None:
            return DefaultPairParams(ccy_pair=ccy_pair_upper)

        is_cny_quoted = ccy_pair_upper in CNY_QUOTED_PAIRS

        if is_cny_quoted:
            result = self.curve_service.resolve_valuation_params(
                session, valuation_date, base,
                _REPRESENTATIVE_MATURITY_YEARS,
            )
            if result:
                spot = result.get("spot_rate")
                vol = result.get("volatility")
                rf_base = result.get("rf_rate_base")
                rf_quote = result.get("rf_rate_quote")
                curve_date = result.get("curve_date")
        else:
            er_spot = self.exchange_rate_service.get_rate(
                session, ccy_pair_upper, valuation_date,
            )
            if er_spot is not None:
                spot = er_spot

            if base != "CNY":
                base_res = self.curve_service.resolve_valuation_params(
                    session, valuation_date, base,
                    _REPRESENTATIVE_MATURITY_YEARS,
                )
                if base_res:
                    rf_base = base_res.get("rf_rate_base")
                    if curve_date is None:
                        curve_date = base_res.get("curve_date")
                    if vol is None:
                        vol = base_res.get("volatility")

            if quote != "CNY":
                quote_res = self.curve_service.resolve_valuation_params(
                    session, valuation_date, quote,
                    _REPRESENTATIVE_MATURITY_YEARS,
                )
                if quote_res:
                    rf_quote = quote_res.get("rf_rate_base")
                    if curve_date is None:
                        curve_date = quote_res.get("curve_date")
                    if vol is None:
                        vol = quote_res.get("volatility")
            else:
                base_res = self.curve_service.resolve_valuation_params(
                    session, valuation_date, base,
                    _REPRESENTATIVE_MATURITY_YEARS,
                )
                if base_res:
                    rf_quote = base_res.get("rf_rate_quote")
                    if curve_date is None:
                        curve_date = base_res.get("curve_date")

        return DefaultPairParams(
            ccy_pair=ccy_pair_upper,
            spot=spot,
            volatility=vol,
            rf_rate_base=rf_base,
            rf_rate_quote=rf_quote,
            curve_date=curve_date,
        )

    # ── custom scenario analysis ───────────────────────────────────

    def analyze_custom_scenario(
        self,
        session: Session,
        request: ScenarioAnalysisRequest,
        scenario_id: str | None = None,
        scenario_name: str | None = None,
    ) -> ScenarioAnalysisResponse:
        """Run a single scenario analysis with pair-level overrides."""
        portfolio_ids = request.portfolio_ids
        if portfolio_ids is None:
            portfolio_ids = _all_portfolio_ids(session)
        if not portfolio_ids:
            return self._empty_response(request, scenario_id, scenario_name)

        pair_override_map: dict[str, CcyPairScenarioOverride] = {}
        for po in request.pair_overrides:
            pair_override_map[po.ccy_pair.upper()] = po

        pair_spot_override: dict[str, float] = {}
        pair_fx_override_ccy_to_cny: dict[str, float] = {}
        trade_overrides: list[OptionTradeParamsOverride] = []

        # Expand pair overrides → trade-level + spot/fx maps
        option_trades = session.exec(
            select(OptionTrade).where(
                OptionTrade.portfolio_id.in_(portfolio_ids),
                OptionTrade.trade_date <= request.valuation_date,
            )
        ).all()

        for trade in option_trades:
            ccy_pair = (trade.ccy_pair or "").upper()
            if ccy_pair not in pair_override_map:
                continue

            po = pair_override_map[ccy_pair]
            override = OptionTradeParamsOverride(trade_id=trade.id)
            has_override = False

            if po.spot is not None:
                override.spot = po.spot
                has_override = True
            if po.volatility is not None:
                override.volatility = po.volatility
                has_override = True
            if po.rf_rate_base is not None:
                override.rf_rate_base = po.rf_rate_base
                has_override = True
            if po.rf_rate_quote is not None:
                override.rf_rate_quote = po.rf_rate_quote
                has_override = True

            if has_override:
                trade_overrides.append(override)

        # Build spot override map (for spot trade P&L)
        # Build fx override map (for CNY conversion)
        for po in request.pair_overrides:
            upper = po.ccy_pair.upper()
            if po.spot is not None:
                pair_spot_override[upper] = po.spot

                base, _quote = _split_ccy(upper)
                if base and upper in CNY_QUOTED_PAIRS:
                    pair_fx_override_ccy_to_cny[base] = po.spot

        # Build aggregated-analysis request and call the existing pipeline
        agg_request = AggregatedAnalysisRequest(
            portfolio_ids=portfolio_ids,
            start_date=request.start_date,
            valuation_date=request.valuation_date,
            curve_type=request.curve_type,
            trade_params=trade_overrides,
        )

        agg_response = self._portfolio_service.calculate_aggregated_analysis(
            session, agg_request,
            pair_spot_override=pair_spot_override if pair_spot_override else None,
            pair_fx_override_ccy_to_cny=(
                pair_fx_override_ccy_to_cny if pair_fx_override_ccy_to_cny else None
            ),
        )

        return ScenarioAnalysisResponse(
            **agg_response.model_dump(),
            scenario_id=scenario_id,
            scenario_name=scenario_name,
        )

    # ── builtin scenarios ─────────────────────────────────────────

    def analyze_builtin_scenarios(
        self,
        session: Session,
        request: BuiltinScenariosRequest,
    ) -> BuiltinScenariosResponse:
        """Run all builtin scenarios and return results."""
        portfolio_ids = request.portfolio_ids
        if portfolio_ids is None:
            portfolio_ids = _all_portfolio_ids(session)

        if not portfolio_ids:
            empty = self._empty_response(
                ScenarioAnalysisRequest(
                    portfolio_ids=portfolio_ids,
                    start_date=request.start_date,
                    valuation_date=request.valuation_date,
                    curve_type=request.curve_type,
                ),
            )
            return BuiltinScenariosResponse(baseline=empty, scenarios=[])

        # Baseline (no overrides)
        base_req = ScenarioAnalysisRequest(
            portfolio_ids=portfolio_ids,
            start_date=request.start_date,
            valuation_date=request.valuation_date,
            curve_type=request.curve_type,
        )
        baseline = self.analyze_custom_scenario(
            session, base_req, scenario_id="base", scenario_name="基准情景",
        )

        # Resolve default params for all required pairs
        required = self.extract_required_pairs(
            session, portfolio_ids, request.valuation_date,
        )
        default_params: dict[str, DefaultPairParams] = {}
        for pair in required.all_pairs:
            default_params[pair] = self.resolve_default_pair_params(
                session, pair, request.valuation_date, request.curve_type,
            )

        scenarios: list[ScenarioAnalysisResponse] = []
        for sc_id, sc_name, is_vol_rel, vol_factor, is_spot_rel, spot_factor in BUILTIN_SCENARIOS:
            if sc_id == "base":
                continue

            overrides: list[CcyPairScenarioOverride] = []
            for pair, params in default_params.items():
                po = CcyPairScenarioOverride(ccy_pair=pair)

                if params.volatility is not None:
                    if is_vol_rel:
                        po.volatility = params.volatility * vol_factor
                if params.spot is not None:
                    if is_spot_rel:
                        po.spot = params.spot * spot_factor
                if params.rf_rate_base is not None:
                    po.rf_rate_base = params.rf_rate_base
                if params.rf_rate_quote is not None:
                    po.rf_rate_quote = params.rf_rate_quote

                has_any = (
                    po.spot is not None or po.volatility is not None
                    or po.rf_rate_base is not None or po.rf_rate_quote is not None
                )
                if has_any:
                    overrides.append(po)

            scenario_req = ScenarioAnalysisRequest(
                portfolio_ids=portfolio_ids,
                start_date=request.start_date,
                valuation_date=request.valuation_date,
                curve_type=request.curve_type,
                pair_overrides=overrides,
            )
            result = self.analyze_custom_scenario(
                session, scenario_req, scenario_id=sc_id, scenario_name=sc_name,
            )
            scenarios.append(result)

        return BuiltinScenariosResponse(
            baseline=baseline,
            scenarios=scenarios,
        )

    # ── sweep analysis ───────────────────────────────────────────

    def analyze_sweep(
        self,
        session: Session,
        request: "ScenarioSweepRequest",
    ) -> "ScenarioSweepResponse":
        """Sweep one variable across a range for a single currency pair."""
        from app.schemas.scenario import (
            ScenarioSweepRequest,
            ScenarioSweepResponse,
            SweepStepResult,
        )

        portfolio_ids = request.portfolio_ids
        if portfolio_ids is None:
            portfolio_ids = _all_portfolio_ids(session)

        num_steps = max(2, min(request.num_steps, 100))
        sweep_points: list[float] = [
            round(request.min_value + (request.max_value - request.min_value) * i / (num_steps - 1), 6)
            for i in range(num_steps)
        ]

        results: list[SweepStepResult] = []
        for val in sweep_points:
            po = CcyPairScenarioOverride(ccy_pair=request.ccy_pair)
            if request.variable == "spot":
                po.spot = val
            elif request.variable == "volatility":
                po.volatility = val
            elif request.variable == "rf_rate_base":
                po.rf_rate_base = val
            elif request.variable == "rf_rate_quote":
                po.rf_rate_quote = val

            scenario_req = ScenarioAnalysisRequest(
                portfolio_ids=portfolio_ids,
                start_date=request.start_date,
                valuation_date=request.valuation_date,
                curve_type=request.curve_type,
                pair_overrides=[po],
            )
            scenario_result = self.analyze_custom_scenario(
                session, scenario_req,
            )
            results.append(SweepStepResult(
                variable_value=val,
                summary=scenario_result.summary,
            ))

        return ScenarioSweepResponse(
            ccy_pair=request.ccy_pair,
            variable=request.variable,
            sweep_points=sweep_points,
            results=results,
        )

    # ── earliest trade date ───────────────────────────────────────

    def earliest_trade_date(self, session: Session) -> EarliestTradeDateResponse:
        return EarliestTradeDateResponse(
            earliest_trade_date=_global_earliest_trade_date(session),
        )

    # ── helpers ───────────────────────────────────────────────────

    def _empty_response(
        self,
        request: ScenarioAnalysisRequest,
        scenario_id: str | None = None,
        scenario_name: str | None = None,
    ) -> ScenarioAnalysisResponse:
        """Return an empty scenario response."""
        from app.schemas.portfolio import AggregatedSummary

        TARGET = {"CNY", "USD", "HKD", "EUR", "JPY", "GBP"}
        import datetime as _dt
        return ScenarioAnalysisResponse(
            portfolio_name="",
            portfolio_count=0,
            option_trade_count=0,
            spot_trade_count=0,
            swap_trade_count=0,
            start_date=request.start_date,
            valuation_date=request.valuation_date,
            curve_type=request.curve_type,
            curve_valuation_date=None,
            summary=AggregatedSummary(
                option_metrics_by_ccy_pair=[],
                total_option_pnl_cny=0.0,
                total_spot_pnl_cny=0.0,
                total_swap_pnl_cny=0.0,
                total_pnl_cny=0.0,
                currency_exposures={c: 0.0 for c in TARGET},
            ),
            option_trades=[],
            spot_trades=[],
            swap_trades=[],
            scenario_id=scenario_id,
            scenario_name=scenario_name,
        )


scenario_service = ScenarioService()
