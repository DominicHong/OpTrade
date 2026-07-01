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
  option_trade_count: number
  spot_trade_count: number
  total_portfolios: number
  total_counterparties: number
}

export interface DashboardAnalysisRequest {
  start_date: string | null
  valuation_date: string
  curve_type: string | null
}

export interface DashboardDefaultsResponse {
  earliest_trade_date: string | null
  curve_type: string | null
}
