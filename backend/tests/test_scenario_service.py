"""Tests for scenario analysis service and API."""

import math
from datetime import date, timedelta

import pytest
from sqlmodel import Session, select

from app.models import Portfolio, OptionTrade, SpotTrade, SwapTrade
from app.models.curve import FxImpliedRate
from app.models.exchange_rate import ExchangeRate
from app.schemas.scenario import (
    BuiltinScenariosRequest,
    BuiltinScenariosResponse,
    CcyPairScenarioOverride,
    ScenarioAnalysisRequest,
    ScenarioAnalysisResponse,
)
from app.services.scenario_service import ScenarioService, BUILTIN_SCENARIOS


def _today(days_offset: int = 0) -> date:
    return date.today() + timedelta(days=days_offset)


# ── data fixtures ──────────────────────────────────────────────────


@pytest.fixture
def fx_curve_data(session: Session) -> list[FxImpliedRate]:
    spots = {
        "USD": 7.1000,
        "EUR": 7.8000,
        "HKD": 0.9100,
        "JPY": 0.0460,
        "GBP": 9.0500,
    }
    tenors = ["1W", "1M", "3M", "6M", "1Y", "2Y"]
    tenor_rates = {
        "1W":  (3.80, 1.80),
        "1M":  (4.00, 2.00),
        "3M":  (4.20, 2.10),
        "6M":  (4.50, 2.30),
        "1Y":  (4.80, 2.50),
        "2Y":  (5.00, 2.70),
    }

    records: list[FxImpliedRate] = []
    for days_ago in range(250):
        curve_date = _today(-days_ago)
        for ccy, spot in spots.items():
            varied_spot = spot * (1.0 + 0.005 * math.sin(days_ago * 0.1))
            for tenor in tenors:
                fir, cnyr = tenor_rates[tenor]
                records.append(
                    FxImpliedRate(
                        curve_date=curve_date,
                        tenor=tenor,
                        foreign_currency=ccy,
                        foreign_implied_rate=fir,
                        cny_risk_free_rate=cnyr,
                        spot_rate=varied_spot,
                        swap_points=0.0,
                        source="test",
                    )
                )
    for r in records:
        session.add(r)
    session.commit()
    return records


@pytest.fixture
def exchange_rates(session: Session) -> list[ExchangeRate]:
    rate_date = _today(-1)
    rates = [
        ExchangeRate(rate_date=rate_date, ccy_pair="EUR/USD", rate=1.1000, source="test"),
        ExchangeRate(rate_date=rate_date, ccy_pair="USD/HKD", rate=7.8300, source="test"),
        ExchangeRate(rate_date=rate_date, ccy_pair="EUR/CNY", rate=7.8050, source="test"),
    ]
    for r in rates:
        session.add(r)
    session.commit()
    return rates


@pytest.fixture
def portfolio_with_trades(session: Session, fx_curve_data, exchange_rates) -> Portfolio:
    pf = Portfolio(name="ScenarioTest")
    session.add(pf)
    session.commit()
    session.refresh(pf)

    expiry = _today(90)

    # USD/CNY CALL option
    opt = OptionTrade(
        portfolio_id=pf.id,
        trade_id="OPT-USDCNY-1",
        ccy_pair="USD/CNY",
        trade_type="CALL",
        direction="Buy",
        strike=7.1000,
        notional1=1_000_000.0,
        trade_date=_today(-30),
        expiry_date=expiry,
        option_category="fx_vanilla",
        premium_amount=50000.0,
        premium_currency="CNY",
    )
    session.add(opt)

    # EUR/CNY PUT option
    opt2 = OptionTrade(
        portfolio_id=pf.id,
        trade_id="OPT-EURCNY-1",
        ccy_pair="EUR/CNY",
        trade_type="PUT",
        direction="Sell",
        strike=7.8000,
        notional1=500_000.0,
        trade_date=_today(-30),
        expiry_date=expiry,
        option_category="fx_vanilla",
        premium_amount=30000.0,
        premium_currency="CNY",
    )
    session.add(opt2)

    # USD/CNY spot trade
    spot = SpotTrade(
        portfolio_id=pf.id,
        trade_id="SPOT-USDCNY-1",
        ccy_pair="USD/CNY",
        direction="Buy",
        deal_price=7.1000,
        ccy1_amount=1_000_000.0,
        ccy2_amount=7_100_000.0,
        ccy1="USD",
        ccy2="CNY",
        trade_date=_today(-10),
        settlement_date=_today(-8),
    )
    session.add(spot)

    # EUR/USD spot trade (cross pair → derives EUR/CNY and USD/CNY pairs)
    spot_cross = SpotTrade(
        portfolio_id=pf.id,
        trade_id="SPOT-EURUSD-1",
        ccy_pair="EUR/USD",
        direction="Buy",
        deal_price=1.1000,
        ccy1_amount=100_000.0,
        ccy2_amount=110_000.0,
        ccy1="EUR",
        ccy2="USD",
        trade_date=_today(-5),
        settlement_date=_today(-3),
    )
    session.add(spot_cross)

    # USD/CNY swap trade
    swap = SwapTrade(
        portfolio_id=pf.id,
        trade_id="SWAP-USDCNY-1",
        ccy_pair="USD/CNY",
        direction="Buy/Sell",
        near_value_date=_today(-15),
        far_value_date=_today(30),
        near_deal_price=7.1000,
        far_deal_price=7.1200,
        near_ccy1_amount=1_000_000.0,
        near_ccy2_amount=7_100_000.0,
        far_ccy1_amount=1_000_000.0,
        far_ccy2_amount=7_120_000.0,
        ccy1="USD",
        ccy2="CNY",
        trade_date=_today(-20),
        spread=200.0,
    )
    session.add(swap)

    session.commit()
    session.refresh(pf)
    return pf


# ── extract_required_pairs ─────────────────────────────────────────


class TestExtractRequiredPairs:

    def test_extracts_option_spot_swap_pairs(self, session, portfolio_with_trades):
        svc = ScenarioService()
        result = svc.extract_required_pairs(
            session, [portfolio_with_trades.id], _today(),
        )

        assert "USD/CNY" in result.option_pairs
        assert "EUR/CNY" in result.option_pairs
        assert "USD/CNY" in result.spot_pairs
        assert "EUR/USD" in result.spot_pairs
        assert "USD/CNY" in result.swap_pairs

    def test_derives_ccy_to_cny_pairs_from_spot_exposure(
        self, session, portfolio_with_trades,
    ):
        svc = ScenarioService()
        result = svc.extract_required_pairs(
            session, [portfolio_with_trades.id], _today(),
        )

        assert "EUR/CNY" in result.derived_ccy_to_cny_pairs
        assert "USD/CNY" in result.derived_ccy_to_cny_pairs

    def test_all_pairs_is_sorted_union(self, session, portfolio_with_trades):
        svc = ScenarioService()
        result = svc.extract_required_pairs(
            session, [portfolio_with_trades.id], _today(),
        )

        assert result.all_pairs == sorted(set(
            result.option_pairs + result.spot_pairs
            + result.swap_pairs + result.derived_ccy_to_cny_pairs
        ))

    def test_empty_when_no_portfolios(self, session):
        svc = ScenarioService()
        result = svc.extract_required_pairs(session, [], _today())

        assert result.all_pairs == []
        assert result.option_pairs == []
        assert result.spot_pairs == []
        assert result.swap_pairs == []
        assert result.derived_ccy_to_cny_pairs == []

    def test_none_portfolios_uses_all(self, session, portfolio_with_trades):
        svc = ScenarioService()
        result = svc.extract_required_pairs(session, None, _today())

        assert len(result.all_pairs) > 0
        assert "USD/CNY" in result.all_pairs


# ── resolve_default_pair_params ────────────────────────────────────


class TestResolveDefaultPairParams:

    def test_cny_quoted_pair(self, session, fx_curve_data):
        svc = ScenarioService()
        result = svc.resolve_default_pair_params(
            session, "USD/CNY", _today(-1), "fx_implied_rate",
        )

        assert result.ccy_pair == "USD/CNY"
        assert result.spot is not None
        assert result.spot == pytest.approx(7.1000, rel=0.01)
        assert result.volatility is not None
        assert result.rf_rate_base is not None
        assert result.rf_rate_quote is not None

    def test_cross_pair(self, session, fx_curve_data, exchange_rates):
        svc = ScenarioService()
        result = svc.resolve_default_pair_params(
            session, "EUR/USD", _today(-1), "fx_implied_rate",
        )

        assert result.ccy_pair == "EUR/USD"
        assert result.spot is not None
        assert result.spot == pytest.approx(1.1000, rel=0.01)

    def test_unknown_pair_returns_none_params(self, session, fx_curve_data):
        svc = ScenarioService()
        result = svc.resolve_default_pair_params(
            session, "ZZZ/CNY", _today(-1), "fx_implied_rate",
        )

        assert result.spot is None


# ── analyze_custom_scenario ────────────────────────────────────────


class TestAnalyzeCustomScenario:

    def test_no_overrides_produces_valid_result(self, session, portfolio_with_trades):
        svc = ScenarioService()
        req = ScenarioAnalysisRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_custom_scenario(session, req)

        assert isinstance(result, ScenarioAnalysisResponse)
        assert result.portfolio_count == 1
        assert result.option_trade_count >= 2
        assert result.spot_trade_count >= 2
        assert result.swap_trade_count >= 1
        assert result.summary.total_pnl_cny is not None

    def test_spot_override_flows_to_result(self, session, portfolio_with_trades):
        svc = ScenarioService()
        req = ScenarioAnalysisRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
            pair_overrides=[
                CcyPairScenarioOverride(ccy_pair="USD/CNY", spot=7.5000),
            ],
        )
        result = svc.analyze_custom_scenario(
            session, req, scenario_id="test", scenario_name="测试",
        )

        assert result.scenario_id == "test"
        assert result.scenario_name == "测试"
        assert result.summary.total_pnl_cny is not None

    def test_vol_override_changes_option_pnl(self, session, portfolio_with_trades):
        svc = ScenarioService()

        base_req = ScenarioAnalysisRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        base = svc.analyze_custom_scenario(session, base_req, scenario_id="base")

        high_vol_req = ScenarioAnalysisRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
            pair_overrides=[
                CcyPairScenarioOverride(ccy_pair="USD/CNY", volatility=0.50),
            ],
        )
        high_vol = svc.analyze_custom_scenario(
            session, high_vol_req, scenario_id="high_vol",
        )

        assert base.summary.total_option_pnl_cny != pytest.approx(
            high_vol.summary.total_option_pnl_cny, abs=0.01,
        )

    def test_empty_when_no_portfolios(self, session):
        svc = ScenarioService()
        req = ScenarioAnalysisRequest(
            portfolio_ids=[],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_custom_scenario(session, req)

        assert result.portfolio_count == 0
        assert result.option_trade_count == 0
        assert result.summary.total_pnl_cny == 0.0

    def test_none_portfolio_uses_all(self, session, portfolio_with_trades):
        svc = ScenarioService()
        req = ScenarioAnalysisRequest(
            portfolio_ids=None,
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_custom_scenario(session, req)

        assert result.portfolio_count >= 1


# ── analyze_builtin_scenarios ──────────────────────────────────────


class TestAnalyzeBuiltinScenarios:

    def test_returns_baseline_and_non_base_scenarios(self, session, portfolio_with_trades):
        svc = ScenarioService()
        req = BuiltinScenariosRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_builtin_scenarios(session, req)

        assert isinstance(result, BuiltinScenariosResponse)
        assert result.baseline.scenario_id == "base"
        assert result.baseline.scenario_name == "基准情景"
        assert len(result.scenarios) == len(BUILTIN_SCENARIOS) - 1  # exclude "base"
        assert all(s.scenario_id is not None for s in result.scenarios)
        assert all(s.scenario_name is not None for s in result.scenarios)
        assert "vol_up_10" in [s.scenario_id for s in result.scenarios]
        assert "spot_dn_5" in [s.scenario_id for s in result.scenarios]
        assert "vol_up_sp_dn" in [s.scenario_id for s in result.scenarios]

    def test_baseline_is_identical_to_no_override_analyze(
        self, session, portfolio_with_trades,
    ):
        svc = ScenarioService()

        builtin_req = BuiltinScenariosRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        builtin_result = svc.analyze_builtin_scenarios(session, builtin_req)

        direct_req = ScenarioAnalysisRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        direct_result = svc.analyze_custom_scenario(
            session, direct_req, scenario_id="base", scenario_name="基准情景",
        )

        assert builtin_result.baseline.summary.total_pnl_cny == pytest.approx(
            direct_result.summary.total_pnl_cny, rel=0.01,
        )

    def test_vol_scenarios_differ_from_baseline(self, session, portfolio_with_trades):
        svc = ScenarioService()
        req = BuiltinScenariosRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_builtin_scenarios(session, req)

        vol_up_20 = next(s for s in result.scenarios if s.scenario_id == "vol_up_20")
        assert vol_up_20.summary.total_option_pnl_cny != pytest.approx(
            result.baseline.summary.total_option_pnl_cny, abs=0.01,
        )

    def test_spot_scenarios_differ_from_baseline(self, session, portfolio_with_trades):
        svc = ScenarioService()
        req = BuiltinScenariosRequest(
            portfolio_ids=[portfolio_with_trades.id],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_builtin_scenarios(session, req)

        spot_dn_5 = next(s for s in result.scenarios if s.scenario_id == "spot_dn_5")
        assert spot_dn_5.summary.total_pnl_cny != pytest.approx(
            result.baseline.summary.total_pnl_cny, abs=0.01,
        )

    def test_empty_for_no_portfolios(self, session):
        svc = ScenarioService()
        req = BuiltinScenariosRequest(
            portfolio_ids=[],
            valuation_date=_today(),
            curve_type="fx_implied_rate",
        )
        result = svc.analyze_builtin_scenarios(session, req)

        assert result.baseline.portfolio_count == 0
        assert len(result.scenarios) == 0


# ── earliest_trade_date ────────────────────────────────────────────


class TestEarliestTradeDate:

    def test_finds_min_across_all_trade_types(self, session, portfolio_with_trades):
        svc = ScenarioService()
        result = svc.earliest_trade_date(session)

        assert result.earliest_trade_date is not None
        assert isinstance(result.earliest_trade_date, date)

    def test_none_when_no_trades(self, session):
        svc = ScenarioService()
        result = svc.earliest_trade_date(session)

        assert result.earliest_trade_date is None


# ── BUILTIN_SCENARIOS constant ─────────────────────────────────────


class TestBuiltinScenariosConstant:

    def test_has_11_scenarios_including_base(self):
        assert len(BUILTIN_SCENARIOS) == 11

    def test_all_have_id_and_name(self):
        for sid, name, *_ in BUILTIN_SCENARIOS:
            assert isinstance(sid, str)
            assert isinstance(name, str)
            assert len(sid) > 0
            assert len(name) > 0

    def test_base_is_first(self):
        assert BUILTIN_SCENARIOS[0][0] == "base"
