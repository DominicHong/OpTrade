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
  risk_free_rate: number | null
  time_to_expiry_years: number | null
  scenario_label: string
  error: string | null
}

export interface GreeksRequest {
  trade_ids: number[]
  spot?: number | null
  volatility?: number | null
  risk_free_rate?: number | null
  scenario_label?: string
}

export interface PricingRequest {
  option_type: string
  direction: string
  spot: number
  strike: number
  volatility: number
  time_to_expiry_years: number
  risk_free_rate: number
  notional?: number
}

export interface PricingResult {
  npv: number | null
  fair_premium: number | null
  currency: string
  error: string | null
}

export interface ScenarioRequest {
  trade_ids?: number[]
  portfolio_id?: number | null
  shifts?: {
    spot?: number[]
    vol?: number[]
    days_forward?: number[]
  }
  base_spot?: number
  base_vol?: number
  risk_free_rate?: number
  valuation_date?: string | null
}

export interface HeatmapResponse {
  spot_shifts: number[]
  vol_shifts: number[]
  values: number[][]
  base_greeks: GreeksResult | null
}
