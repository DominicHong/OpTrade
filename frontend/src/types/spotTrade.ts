/** Core SpotTrade interface matching backend SpotTradeRead schema. */
export interface SpotTrade {
  id: number
  trade_id: string
  portfolio_id: number | null
  counterparty_id: number | null
  portfolio_name: string | null
  counterparty_name: string | null

  // Trade details
  ccy_pair: string | null
  direction: string | null      // 买入 / 卖出
  event_type: string | null     // 正常 / 期权行权衍生

  deal_price: number | null
  ccy1_amount: number | null
  ccy2_amount: number | null
  ccy1: string | null
  ccy2: string | null

  // Dates
  trade_date: string | null
  settlement_date: string | null

  // Status and meta
  source: string | null
  venue: string | null

  // Timestamps
  created_at: string | null
  updated_at: string | null
}

export interface SpotTradeListResponse {
  data: SpotTrade[]
  total: number
  page: number
  page_size: number
}

export interface SpotTradeFilterParams {
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
  settlement_date_from?: string
  settlement_date_to?: string
  search?: string
}

export interface SpotTradeCreate {
  trade_id: string
  portfolio_id?: number | null
  portfolio_name?: string | null
  counterparty_name?: string | null
  ccy_pair?: string | null
  direction?: string | null
  event_type?: string | null
  deal_price?: number | null
  ccy1_amount?: number | null
  ccy2_amount?: number | null
  trade_date?: string | null
  settlement_date?: string | null
  source?: string | null
  venue?: string | null
}

export interface SpotTradeUpdate {
  trade_id?: string | null
  portfolio_id?: number | null
  portfolio_name?: string | null
  counterparty_name?: string | null
  ccy_pair?: string | null
  direction?: string | null
  event_type?: string | null
  deal_price?: number | null
  ccy1_amount?: number | null
  ccy2_amount?: number | null
  trade_date?: string | null
  settlement_date?: string | null
  source?: string | null
  venue?: string | null
}
