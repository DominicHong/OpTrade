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
