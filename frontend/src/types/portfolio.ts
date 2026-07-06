export interface Portfolio {
  id: number
  name: string
  description: string | null
  trade_count: number
  created_at: string | null
}

export interface PortfolioCreate {
  name: string
  description?: string | null
}

export interface PortfolioGreeksSummary {
  portfolio_id: number
  portfolio_name: string
  trade_count: number
  total_delta: number
  total_gamma: number
  total_vega: number
  total_theta: number
  total_rho: number
  total_npv: number
  breakdown_by_ccy: Record<string, Record<string, number>>
}

// ---------------------------------------------------------------------------
// Curve parameter resolution
// ---------------------------------------------------------------------------

export interface PortfolioResolveRequest {
  valuation_date: string
  curve_type: string
}

export interface OptionTradeParamsResolved {
  trade_id: number
  trade_id_str: string | null
  ccy_pair: string | null
  option_type: string | null
  direction: string | null
  strike: number | null
  notional1: number | null
  expiry_date: string | null
  remaining_maturity_years: number | null
  rf_rate_base: number | null   // decimal
  rf_rate_quote: number | null  // decimal
  spot: number | null
  volatility: number | null     // decimal, annualised
  curve_resolved: boolean
  curve_date: string | null
}

export interface PortfolioResolveResponse {
  valuation_date: string
  curve_type: string
  trades: OptionTradeParamsResolved[]
}

// ---------------------------------------------------------------------------
// Per-option-trade parameter overrides
// ---------------------------------------------------------------------------

export interface OptionTradeParamsOverride {
  trade_id: number
  rf_rate_base: number | null
  rf_rate_quote: number | null
  spot: number | null
  volatility: number | null
}

// ---------------------------------------------------------------------------
// Greeks request / response
// ---------------------------------------------------------------------------

export interface PortfolioGreeksRequest {
  valuation_date?: string | null
  curve_type?: string | null
  trade_params?: OptionTradeParamsOverride[]
}

export interface OptionTradeGreeksDetail {
  trade_id: number
  trade_id_str: string | null
  ccy_pair: string | null
  option_type: string | null
  direction: string | null
  strike: number | null
  notional1: number | null
  delta: number | null
  gamma: number | null
  npv: number | null
  premium: number | null
  profit: number | null
  error: string | null
}

export interface PortfolioGreeksResponse {
  portfolio_id: number
  portfolio_name: string
  trade_count: number
  total_delta: number
  total_gamma: number
  total_npv: number
  total_profit: number
  rf_rate_base: number | null
  rf_rate_quote: number | null
  volatility_used: number | null
  spot_used: number | null
  curve_type: string | null
  curve_valuation_date: string | null
  trades: OptionTradeGreeksDetail[]
}

// ---------------------------------------------------------------------------
// Multi-portfolio aggregated P&L analysis
// ---------------------------------------------------------------------------

export interface AggregatedAnalysisRequest {
  portfolio_ids: number[]
  start_date?: string | null
  valuation_date: string
  curve_type?: string | null
  trade_params?: OptionTradeParamsOverride[]
}

export interface CcyPairOptionMetrics {
  ccy_pair: string
  // (a) CNY-converted P&L items
  npv_cny: number
  premium_pnl_cny: number       // 估值损益
  exercise_pnl_cny: number      // 行权损益
  total_option_pnl_cny: number  // 期权总损益
  // (b) Greeks in original currency (ccy2 / 1 ccy1)
  delta: number
  gamma: number
  // Transparency: FX rate used to convert ccy2 → CNY (1.0 if ccy2 == CNY)
  fx_rate_to_cny: number | null
  trade_count: number
}

export interface AggregatedSummary {
  // (1) Option risk metrics — one entry per currency pair
  option_metrics_by_ccy_pair: CcyPairOptionMetrics[]
  // (2) Portfolio-level P&L (all CNY)
  total_option_pnl_cny: number
  total_spot_pnl_cny: number
  total_swap_pnl_cny: number
  total_pnl_cny: number
  // (3) Spot currency exposures (raw)
  currency_exposures: Record<string, number>
}

export interface OptionTradeAnalysisDetail {
  trade_id: number
  trade_id_str: string | null
  ccy_pair: string | null
  option_type: string | null
  direction: string | null
  strike: number | null
  notional1: number | null
  trade_date: string | null
  expiry_date: string | null
  exercise_status: string | null
  delta: number | null
  gamma: number | null
  npv: number | null
  premium: number | null
  premium_pnl: number | null
  exercise_pnl: number | null
  total_pnl: number | null
  // CNY-converted mirror (null when no FX rate available)
  premium_pnl_cny: number | null
  exercise_pnl_cny: number | null
  total_pnl_cny: number | null
  npv_cny: number | null
  fx_rate_to_cny: number | null
  error: string | null
}

export interface SpotTradeAnalysisDetail {
  trade_id: number
  trade_id_str: string | null
  ccy_pair: string | null
  direction: string | null
  deal_price: number | null
  market_rate: number | null
  adjusted_deal_price: number | null
  notional: number | null
  trade_date: string | null
  settlement_date: string | null
  pnl: number | null
  // CNY-converted mirror
  pnl_cny: number | null
  fx_rate_to_cny: number | null
  is_derivative: boolean
  error: string | null
}

export interface SwapTradeAnalysisDetail {
  trade_id: number
  trade_id_str: string | null
  ccy_pair: string | null
  direction: string | null
  near_deal_price: number | null
  far_deal_price: number | null
  near_value_date: string | null
  far_value_date: string | null
  notional: number | null
  trade_date: string | null
  status: string | null         // 未起息 / 存续 / 到期
  pnl: number | null            // original currency (ccy2)
  pnl_cny: number | null
  return_rate: number | null    // annualised percent, 2 decimals
  fx_rate_to_cny: number | null
  error: string | null
}

export interface AggregatedAnalysisResponse {
  portfolio_name: string
  portfolio_count: number
  option_trade_count: number
  spot_trade_count: number
  swap_trade_count: number
  start_date: string | null
  valuation_date: string | null
  curve_type: string | null
  curve_valuation_date: string | null
  summary: AggregatedSummary
  option_trades: OptionTradeAnalysisDetail[]
  spot_trades: SpotTradeAnalysisDetail[]
  swap_trades: SwapTradeAnalysisDetail[]
}
