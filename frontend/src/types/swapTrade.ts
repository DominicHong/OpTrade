/** Core SwapTrade interface matching backend SwapTradeRead schema. */
export interface SwapTrade {
  id: number
  trade_id: string
  portfolio_id: number | null
  counterparty_id: number | null
  portfolio_name: string | null
  counterparty_name: string | null

  // Identifiers
  source_trade_id: string | null
  review_id: string | null

  // Trade details
  ccy_pair: string | null
  direction: string | null      // Buy/Sell | Sell/Buy
  swap_type: string | null
  event_type: string | null
  tenor: string | null
  spread: number | null

  ccy1: string | null
  ccy2: string | null

  // Spot reference
  spot_value_date: string | null
  spot_rate: number | null

  // Near leg
  near_value_date: string | null
  near_tenor: string | null
  near_swap_points: number | null
  near_deal_price: number | null
  near_trade_ccy: string | null
  near_ccy1_amount: number | null
  near_ccy2_amount: number | null
  near_settlement_status: string | null

  // Far leg
  far_value_date: string | null
  far_tenor: string | null
  far_swap_points: number | null
  far_deal_price: number | null
  far_trade_ccy: string | null
  far_ccy1_amount: number | null
  far_ccy2_amount: number | null
  far_settlement_status: string | null

  // Dates
  trade_date: string | null
  trade_time: string | null
  natural_date: string | null

  // Status and meta
  our_trader: string | null
  venue: string | null
  clearing_org: string | null
  clearing_method: string | null
  source: string | null
  comments: string | null

  // Timestamps
  created_at: string | null
  updated_at: string | null
}

export interface SwapTradeListResponse {
  data: SwapTrade[]
  total: number
  page: number
  page_size: number
}

export interface SwapTradeFilterParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
  portfolio_id?: number | null
  counterparty_id?: number | null
  ccy_pair?: string
  direction?: string
  event_type?: string
  trade_date_from?: string
  trade_date_to?: string
  near_value_date_from?: string
  near_value_date_to?: string
  search?: string
}

export interface SwapTradeCreate {
  trade_id: string
  portfolio_id?: number | null
  portfolio_name?: string | null
  counterparty_name?: string | null
  source_trade_id?: string | null
  review_id?: string | null
  ccy_pair?: string | null
  direction?: string | null
  swap_type?: string | null
  event_type?: string | null
  tenor?: string | null
  spread?: number | null
  spot_value_date?: string | null
  spot_rate?: number | null
  near_value_date?: string | null
  near_tenor?: string | null
  near_swap_points?: number | null
  near_deal_price?: number | null
  near_trade_ccy?: string | null
  near_ccy1_amount?: number | null
  near_ccy2_amount?: number | null
  near_settlement_status?: string | null
  far_value_date?: string | null
  far_tenor?: string | null
  far_swap_points?: number | null
  far_deal_price?: number | null
  far_trade_ccy?: string | null
  far_ccy1_amount?: number | null
  far_ccy2_amount?: number | null
  far_settlement_status?: string | null
  trade_date?: string | null
  trade_time?: string | null
  natural_date?: string | null
  our_trader?: string | null
  venue?: string | null
  clearing_org?: string | null
  clearing_method?: string | null
  source?: string | null
  comments?: string | null
}

export interface SwapTradeUpdate {
  trade_id?: string | null
  portfolio_id?: number | null
  portfolio_name?: string | null
  counterparty_name?: string | null
  source_trade_id?: string | null
  review_id?: string | null
  ccy_pair?: string | null
  direction?: string | null
  swap_type?: string | null
  event_type?: string | null
  tenor?: string | null
  spread?: number | null
  spot_value_date?: string | null
  spot_rate?: number | null
  near_value_date?: string | null
  near_tenor?: string | null
  near_swap_points?: number | null
  near_deal_price?: number | null
  near_trade_ccy?: string | null
  near_ccy1_amount?: number | null
  near_ccy2_amount?: number | null
  near_settlement_status?: string | null
  far_value_date?: string | null
  far_tenor?: string | null
  far_swap_points?: number | null
  far_deal_price?: number | null
  far_trade_ccy?: string | null
  far_ccy1_amount?: number | null
  far_ccy2_amount?: number | null
  far_settlement_status?: string | null
  trade_date?: string | null
  trade_time?: string | null
  natural_date?: string | null
  our_trader?: string | null
  venue?: string | null
  clearing_org?: string | null
  clearing_method?: string | null
  source?: string | null
  comments?: string | null
}
