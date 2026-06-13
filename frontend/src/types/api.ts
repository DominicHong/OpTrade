/** Generic paginated API response wrapper. */
export interface ApiResponse<T> {
  data: T
  total?: number
  page?: number
  page_size?: number
}

/** Import-related types. */
export interface ImportHistoryItem {
  id: number
  filename: string
  total_rows: number
  imported_rows: number
  error_rows: number
  status: string
  created_at: string
}

export interface ImportParsedRow {
  row_number: number
  trade_id: string | null
  data: Record<string, string>
  errors: string[]
}

export interface ImportPreviewResponse {
  import_log_id: number
  filename: string
  total_rows: number
  valid_rows: number
  error_rows: number
  column_mapping: Record<string, string>
  parsed_rows: ImportParsedRow[]
  errors: Record<string, unknown>[]
}

/** Response after upload completes (includes import results). */
export interface ImportConfirmResponse {
  import_log_id: number
  filename: string
  total_rows: number
  imported_rows: number
  skipped_rows: number
  error_rows: number
  status: string
  errors: Record<string, unknown>[]
  error_message?: string | null
}

/** Dashboard types. */
export interface DashboardSummary {
  total_trades: number
  total_portfolios: number
  total_counterparties: number
  total_notional1: number
  notional_by_ccy: Record<string, number>
  trades_by_type: Record<string, number>
  trades_by_status: Record<string, number>
}

export interface RiskMetricsSummary {
  total_delta: number
  total_gamma: number
  total_vega: number
  total_theta: number
  total_rho: number
  total_npv: number
  trade_count_with_greeks: number
}

export interface ExpiryProfile {
  bucket: string
  trade_count: number
  total_notional: number
  total_delta: number
  total_gamma: number
}
