/** Curve management type definitions. */

export interface CurveDefinition {
  id: number
  name: string
  curve_type: string
  description: string | null
  source_url: string | null
  is_active: boolean
}

export interface FxImpliedRate {
  id: number
  curve_date: string
  tenor: string
  foreign_currency: string
  foreign_implied_rate: number | null
  cny_risk_free_rate: number | null
  spot_rate: number | null
  swap_points: number | null
  source: string | null
  created_at: string | null
}

export interface FxImpliedRateFilterParams {
  date_from?: string | null
  date_to?: string | null
  currency?: string | null
  tenor?: string | null
  page?: number
  page_size?: number
}

export interface FxImpliedRateListResponse {
  data: FxImpliedRate[]
  total: number
  page: number
  page_size: number
}

export interface CurveCoverageSummary {
  total_records: number
  date_from: string | null
  date_to: string | null
  currency_count: number
  currencies: string[]
  tenors: string[]
  last_updated: string | null
}

export interface CrawlResult {
  status: 'success' | 'partial' | 'error'
  dates_fetched: string[]
  dates_skipped: string[]
  records_added: number
  error_message: string | null
}

export interface UploadResult {
  records_added: number
  message: string
}
