/** Greek display names. */
export const GREEK_NAMES: Record<string, string> = {
  delta: 'Delta (Δ)',
  gamma: 'Gamma (Γ)',
  vega: 'Vega (ν)',
  theta: 'Theta (Θ)',
  rho: 'Rho (ρ)',
  npv: 'NPV',
}

/** Option type labels. */
export const OPTION_TYPE_LABELS: Record<string, string> = {
  'Plain Vanilla': '普通欧式',
  Barrier: '障碍期权',
  Asian: '亚式期权',
}

/** Direction labels. */
export const DIRECTION_LABELS: Record<string, string> = {
  '买入': 'Buy',
  '卖出': 'Sell',
  'Buy': '买入',
  'Sell': '卖出',
}

/** Trade type labels. */
export const TRADE_TYPE_LABELS: Record<string, string> = {
  'CALL': '看涨 Call',
  'PUT': '看跌 Put',
}

/** Expiry bucket definitions in days. */
export const EXPIRY_BUCKETS = [
  { label: '<1W', maxDays: 7 },
  { label: '1W-1M', maxDays: 30 },
  { label: '1M-3M', maxDays: 90 },
  { label: '3M-6M', maxDays: 180 },
  { label: '6M-1Y', maxDays: 365 },
  { label: '>1Y', maxDays: Infinity },
]

/** Default scenario spot shifts (in pips/bps). */
export const DEFAULT_SPOT_SHIFTS = [-500, -200, -100, -50, 0, 50, 100, 200, 500]

/** Default scenario vol shifts (absolute). */
export const DEFAULT_VOL_SHIFTS = [-0.05, -0.02, -0.01, 0, 0.01, 0.02, 0.05]

/** Default time decay horizons (in days). */
export const DEFAULT_TIME_HORIZONS = [0, 7, 14, 30, 60, 90]
