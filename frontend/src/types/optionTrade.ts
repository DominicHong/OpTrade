/** Core OptionTrade interface matching backend OptionTradeRead schema. */
export interface OptionTrade {
  id: number
  trade_id: string
  source_trade_id: string | null
  review_id: string | null
  leg: string | null
  portfolio_id: number | null
  counterparty_id: number | null
  portfolio_name: string | null
  counterparty_name: string | null

  // Polymorphic discriminator
  option_category: string

  // Option specs
  option_type: string | null
  trade_type: string | null   // CALL / PUT
  direction: string | null     // 买入 / 卖出
  strike: number | null
  ccy_pair: string | null
  trade_currency: string | null

  // Notional
  notional1: number | null
  notional2: number | null

  // Dates
  trade_date: string | null
  expiry_date: string | null
  delivery_date: string | null
  premium_payment_date: string | null

  // Premium
  premium_type: string | null
  premium_rate: number | null
  premium_amount: number | null
  premium_currency: string | null

  // Market data
  spot_rate: number | null
  volatility: number | null

  // Status
  exercise_status: string | null
  effective_status: string | null
  allocation_status: string | null

  // Venue
  venue: string | null
  clearing_method: string | null

  // Meta
  tenor: string | null
  event_type: string | null
  trade_purpose: string | null
  operator: string | null
  source: string | null
  comments: string | null

  // Timestamps
  created_at: string | null
  updated_at: string | null
}

export interface OptionTradeListResponse {
  data: OptionTrade[]
  total: number
  page: number
  page_size: number
}

export interface OptionTradeFilterParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
  portfolio_id?: number | null
  counterparty_id?: number | null
  ccy_pair?: string
  option_type?: string
  trade_type?: string
  direction?: string
  expiry_from?: string
  expiry_to?: string
  trade_date_from?: string
  trade_date_to?: string
  search?: string
  exercise_status?: string
  option_category?: string
}

export interface OptionTradeCreate {
  trade_id: string
  option_category?: string
  source_trade_id?: string | null
  review_id?: string | null
  leg?: string | null
  portfolio_id?: number | null
  portfolio_name?: string | null
  counterparty_name?: string | null
  option_type?: string | null
  trade_type?: string | null
  direction?: string | null
  strike?: number | null
  ccy_pair?: string | null
  trade_currency?: string | null
  notional1?: number | null
  notional2?: number | null
  trade_date?: string | null
  expiry_date?: string | null
  delivery_date?: string | null
  premium_payment_date?: string | null
  premium_type?: string | null
  premium_rate?: number | null
  premium_amount?: number | null
  premium_currency?: string | null
  spot_rate?: number | null
  volatility?: number | null
  exercise_status?: string | null
  effective_status?: string | null
  allocation_status?: string | null
  venue?: string | null
  clearing_method?: string | null
  tenor?: string | null
  event_type?: string | null
  trade_purpose?: string | null
  operator?: string | null
  source?: string | null
  comments?: string | null
}

export interface OptionTradeUpdate {
  trade_id?: string | null
  option_category?: string
  source_trade_id?: string | null
  review_id?: string | null
  leg?: string | null
  portfolio_id?: number | null
  portfolio_name?: string | null
  counterparty_name?: string | null
  option_type?: string | null
  trade_type?: string | null
  direction?: string | null
  strike?: number | null
  ccy_pair?: string | null
  trade_currency?: string | null
  notional1?: number | null
  notional2?: number | null
  trade_date?: string | null
  expiry_date?: string | null
  delivery_date?: string | null
  premium_payment_date?: string | null
  premium_type?: string | null
  premium_rate?: number | null
  premium_amount?: number | null
  premium_currency?: string | null
  spot_rate?: number | null
  volatility?: number | null
  exercise_status?: string | null
  effective_status?: string | null
  allocation_status?: string | null
  venue?: string | null
  clearing_method?: string | null
  tenor?: string | null
  event_type?: string | null
  trade_purpose?: string | null
  operator?: string | null
  source?: string | null
  comments?: string | null
}
