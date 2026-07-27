/** Scenario analysis types — mirrors backend app/schemas/scenario.py. */

import type {
  AggregatedAnalysisResponse,
  AggregatedSummary,
  CcyPairOptionMetrics,
  OptionTradeAnalysisDetail,
  SpotTradeAnalysisDetail,
  SwapTradeAnalysisDetail,
} from './portfolio'

export type { AggregatedAnalysisResponse, AggregatedSummary, CcyPairOptionMetrics }

// ── Override ───────────────────────────────────────────────────────

export interface CcyPairScenarioOverride {
  ccy_pair: string
  spot?: number | null
  volatility?: number | null
  rf_rate_base?: number | null
  rf_rate_quote?: number | null
}

// ── Requests ───────────────────────────────────────────────────────

export interface ScenarioAnalysisRequest {
  portfolio_ids?: number[] | null
  start_date?: string | null
  valuation_date: string
  curve_type?: string | null
  pair_overrides?: CcyPairScenarioOverride[]
}

export interface BuiltinScenariosRequest {
  portfolio_ids?: number[] | null
  start_date?: string | null
  valuation_date: string
  curve_type?: string | null
}

// ── Responses ──────────────────────────────────────────────────────

export interface ScenarioAnalysisResponse extends AggregatedAnalysisResponse {
  scenario_id: string | null
  scenario_name: string | null
}

export interface BuiltinScenariosResponse {
  baseline: ScenarioAnalysisResponse
  scenarios: ScenarioAnalysisResponse[]
}

export interface RequiredPairsResponse {
  option_pairs: string[]
  spot_pairs: string[]
  swap_pairs: string[]
  derived_ccy_to_cny_pairs: string[]
  all_pairs: string[]
}

export interface DefaultPairParams {
  ccy_pair: string
  spot: number | null
  volatility: number | null
  rf_rate_base: number | null
  rf_rate_quote: number | null
  curve_date: string | null
}

export interface EarliestTradeDateResponse {
  earliest_trade_date: string | null
}

// ── Editable pair scenario (frontend state) ─────────────────────────

export interface EditablePairScenario {
  ccyPair: string
  /** Default values from curve (decimals). */
  defaultSpot: number | null
  defaultVol: number | null  // decimal (0.05 = 5%)
  defaultRfBase: number | null  // decimal
  defaultRfQuote: number | null  // decimal
  /** Current override values (display: spot raw, vol %, rate %). */
  currentSpot: number | null
  currentVol: number | null   // percentage (5.0 = 5%)
  currentRfBase: number | null  // percentage
  currentRfQuote: number | null // percentage
  /** Per-field edited flags. */
  spotEdited: boolean
  volEdited: boolean
  rfBaseEdited: boolean
  rfQuoteEdited: boolean
  curveDate: string | null
}

// ── Builtin scenario labels ────────────────────────────────────────

export interface BuiltinScenarioMeta {
  id: string
  name: string
  description: string
}

export const BUILTIN_SCENARIO_META: BuiltinScenarioMeta[] = [
  { id: 'base', name: '基准情景', description: '不做变动，当前市场参数' },
  { id: 'vol_up_10', name: '波动率上升 +10%', description: '波动率 × 1.10' },
  { id: 'vol_up_20', name: '波动率上升 +20%', description: '波动率 × 1.20' },
  { id: 'vol_dn_10', name: '波动率下降 -10%', description: '波动率 × 0.90' },
  { id: 'vol_dn_20', name: '波动率下降 -20%', description: '波动率 × 0.80' },
  { id: 'spot_up_1', name: '即期升值 +1%', description: '即期 × 1.01' },
  { id: 'spot_up_5', name: '即期升值 +5%', description: '即期 × 1.05' },
  { id: 'spot_dn_1', name: '即期贬值 -1%', description: '即期 × 0.99' },
  { id: 'spot_dn_5', name: '即期贬值 -5%', description: '即期 × 0.95' },
  { id: 'vol_up_sp_dn', name: '波动率+20% & 即期-5%', description: '风险逆转情景' },
  { id: 'vol_up_sp_up', name: '波动率+20% & 即期+5%', description: '正冲击情景' },
]

// ── Sweep analysis ──────────────────────────────────────────────────

export interface ScenarioSweepRequest {
  portfolio_ids?: number[] | null
  start_date?: string | null
  valuation_date: string
  curve_type?: string | null
  ccy_pair: string
  variable: string   // "spot" | "volatility" | "rf_rate_base" | "rf_rate_quote"
  min_value: number
  max_value: number
  num_steps?: number
}

export interface SweepStepResult {
  variable_value: number
  summary: import('./portfolio').AggregatedSummary
}

export interface ScenarioSweepResponse {
  ccy_pair: string
  variable: string
  sweep_points: number[]
  results: SweepStepResult[]
}

export const SWEEP_VARIABLE_LABELS: Record<string, string> = {
  spot: '即期汇率 (Spot)',
  volatility: '波动率 (Vol)',
  rf_rate_base: 'Base 利率',
  rf_rate_quote: 'Quote 利率',
}
