/** Format a number to fixed decimal places, returning '--' for null/undefined. */
export function formatNumber(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined) return '--'
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/** Format a notional / large number with thousands separators. */
export function formatNotional(value: number | null | undefined): string {
  if (value === null || value === undefined) return '--'
  return value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** Format a percentage value (e.g. 0.014 -> '1.40%'). */
export function formatPercent(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined) return '--'
  return (value * 100).toFixed(decimals) + '%'
}

/** Format a Greek value with sign and appropriate decimal places. */
export function formatGreek(value: number | null | undefined, isPercent: boolean = false): string {
  if (value === null || value === undefined) return '--'
  if (isPercent) {
    return (value > 0 ? '+' : '') + (value * 100).toFixed(4) + '%'
  }
  return (value > 0 ? '+' : '') + value.toFixed(4)
}

/** Convert a value to 万 (divide by 10000), returning null for null/undefined. */
export function toWan(value: number | null | undefined): number | null | undefined {
  if (value === null || value === undefined) return value
  return value / 10000
}

/** Format a date string for display. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '--'
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

/** Format an ISO datetime string to Beijing time (YYYY-MM-DD HH:mm:ss).
 *
 * The backend stores `created_at` as UTC but may serialize it as a naive
 * datetime (e.g. "2026-06-26T10:12:35"). JavaScript would interpret that as
 * local time, so we append "Z" when the string lacks timezone info to force
 * UTC parsing before converting to Asia/Shanghai.
 */
export function formatBeijingTime(value: string | null | undefined): string {
  if (!value) return '--'
  const hasTz = /Z|[+-]\d{2}:?\d{2}$/.test(value)
  const iso = hasTz ? value : value + 'Z'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

/** Get CSS class for positive/negative/zero Greek values. */
export function greekColorClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (value > 0) return 'text-positive'
  if (value < 0) return 'text-negative'
  return ''
}

/** Format a number with an em-dash placeholder for null/undefined.
 *
 * Defaults to 4 decimal places (the precision used by most portfolio detail
 * tables).  Callers wanting 2 decimals (e.g. 万-scaled amounts) should pass
 * the second argument explicitly.
 */
export function fmt(value: number | null | undefined, decimals: number = 4): string {
  if (value === null || value === undefined) return '—'
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/** Passthrough date display: returns '—' for empty, otherwise the value as-is. */
export function fmtDate(value: string | null | undefined): string {
  if (!value) return '—'
  return value
}

/** CSS class for positive/negative profit values ('' for zero/null). */
export function profitColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (value > 0) return 'profit-positive'
  if (value < 0) return 'profit-negative'
  return ''
}

/** Whether the option type represents a call. */
export function isCall(optionType: string | null | undefined): boolean {
  return !!optionType && optionType.toUpperCase() === 'CALL'
}
