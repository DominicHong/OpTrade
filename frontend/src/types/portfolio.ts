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

export interface PortfolioGreeksRequest {
  rf_rate_base: number
  rf_rate_quote: number
  volatility?: number | null
  spot?: number | null
  valuation_date?: string | null
}

export interface TradeGreeksDetail {
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
  error: string | null
}

export interface PortfolioGreeksResponse {
  portfolio_id: number
  portfolio_name: string
  trade_count: number
  total_delta: number
  total_gamma: number
  total_npv: number
  rf_rate_base: number
  rf_rate_quote: number
  volatility_used: number | null
  spot_used: number | null
  trades: TradeGreeksDetail[]
}
