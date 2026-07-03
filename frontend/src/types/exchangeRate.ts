/** Exchange rate type definitions. */

export interface ExchangeRate {
  id: number
  rate_date: string
  ccy_pair: string
  rate: number
  source: string
  source_ref: string | null
  created_at: string | null
}

export interface ExchangeRateFilterParams {
  date_from?: string | null
  date_to?: string | null
  ccy_pair?: string | null
  source?: string | null
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface ExchangeRateListResponse {
  data: ExchangeRate[]
  total: number
  page: number
  page_size: number
}

export interface ExchangeRateCoverageSummary {
  total_records: number
  date_from: string | null
  date_to: string | null
  ccy_pairs: string[]
  last_updated: string | null
}

export interface ExchangeRateImportResult {
  records_added: number
  records_updated: number
  skipped: number
  message: string
}

export interface ExchangeRateUploadResult {
  records_added: number
  records_updated: number
  skipped: number
  message: string
}

export interface ExchangeRateManualCreate {
  rate_date: string
  ccy_pair: string
  rate: number
  source?: string
  source_ref?: string | null
}

/** 9 supported pairs (AUD/USD deferred — no AUD/CNY source). */
export const SUPPORTED_CCY_PAIRS: string[] = [
  'USD/CNY', 'EUR/CNY', 'HKD/CNY', 'GBP/CNY', 'JPY/CNY',
  'USD/HKD', 'USD/JPY', 'EUR/USD', 'GBP/USD',
]
