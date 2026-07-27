/** Greeks result for a single trade or aggregated. */
export interface GreeksResult {
  trade_id: number
  calculation_date: string
  npv: number | null
  delta: number | null
  gamma: number | null
  vega: number | null
  theta: number | null
  rho: number | null
  spot: number | null
  volatility: number | null
  rf_rate_base: number | null
  rf_rate_quote: number | null
  time_to_expiry_years: number | null
  error: string | null
}

export interface GreeksRequest {
  trade_ids: number[]
  spot?: number | null
  volatility?: number | null
  rf_rate_base?: number | null
  rf_rate_quote?: number | null
}

export interface PricingRequest {
  option_type: string
  direction: string
  spot: number
  strike: number
  volatility: number
  time_to_expiry_years: number
  rf_rate_base: number
  rf_rate_quote: number
  notional?: number
}

export interface PricingResult {
  npv: number | null
  fair_premium: number | null
  currency: string
  error: string | null
}

