import { ref } from 'vue'
import { fetchAggregatedGreeks, fetchPortfolioGreeks, resolvePortfolioParams } from '@/api/portfolios'
import type {
  AggregatedAnalysisRequest,
  AggregatedAnalysisResponse,
  PortfolioGreeksRequest,
  PortfolioGreeksResponse,
  OptionTradeParamsResolved,
  OptionTradeParamsOverride,
} from '@/types/portfolio'

/** Editable per-option-trade params (in display units: % for rates/vol, raw for spot). */
export interface EditableOptionTradeParams {
  tradeId: number
  tradeIdStr: string | null
  ccyPair: string | null
  optionType: string | null
  direction: string | null
  strike: number | null
  notional1: number | null
  expiryDate: string | null
  remainingMaturityYears: number | null
  /** Display value (percentage, e.g. 3.0 = 3%). null = use default. */
  rfRateBase: number | null
  /** Display value (percentage). null = use default. */
  rfRateQuote: number | null
  /** Display value (raw). null = use default. */
  spot: number | null
  /** Display value (percentage). null = use default. */
  volatility: number | null
  curveResolved: boolean
  curveDate: string | null
  /** Per-field flags: true when the user explicitly typed a value (vs. a
   * curve-resolved value echoed back from 获取参数). Only edited fields are
   * sent as overrides so the backend re-resolves the rest from the curve at
   * each date (important for interval P&L, which must use start-date curve
   * data rather than valuation-date echoes). */
  rfRateBaseEdited: boolean
  rfRateQuoteEdited: boolean
  spotEdited: boolean
  volatilityEdited: boolean
}

export function useGreeksCalculation() {
  // Common parameters
  const valuationDate = ref<string>(new Date().toISOString().slice(0, 10))
  const startDate = ref<string | null>(null)
  const curveType = ref<string | null>(null)

  // Multi-portfolio selection
  const selectedPortfolioIds = ref<number[]>([])

  // Per-option-trade params (populated by resolve-params)
  const tradeParams = ref<EditableOptionTradeParams[]>([])

  // Results
  const result = ref<PortfolioGreeksResponse | null>(null)
  const aggregatedResult = ref<AggregatedAnalysisResponse | null>(null)
  const loading = ref(false)
  const resolving = ref(false)
  const error = ref<string | null>(null)

  function resetResult() {
    result.value = null
    error.value = null
  }

  function resetTradeParams() {
    tradeParams.value = []
  }

  /**
   * Validate that every option trade has all four valuation parameters
   * (rfRateBase, rfRateQuote, spot, volatility) filled in — either from
   * curve resolution or by the user. Returns an error message string when
   * validation fails, or null when OK.
   */
  function validateTradeParams(): string | null {
    if (tradeParams.value.length === 0) {
      return '请先点击「获取参数」获取各交易的估值参数，确认或补齐后再计算。'
    }
    const incomplete = tradeParams.value.filter(
      (tp) =>
        tp.rfRateBase == null ||
        tp.rfRateQuote == null ||
        tp.spot == null ||
        tp.volatility == null,
    )
    if (incomplete.length > 0) {
      const ids = incomplete
        .map((tp) => tp.tradeIdStr ?? String(tp.tradeId))
        .join('、')
      return `以下期权缺少估值参数（即期汇率/波动率/Base利率/Quote利率），请在参数表中填写后再计算：${ids}`
    }
    return null
  }

  /** Call the resolve-params endpoint and populate tradeParams. */
  async function resolveParams(portfolioId: number) {
    resolving.value = true
    error.value = null
    try {
      const response = await resolvePortfolioParams(portfolioId, {
        valuation_date: valuationDate.value,
        curve_type: curveType.value || 'fx_implied_rate',
      })

      tradeParams.value = response.trades.map(
        (t: OptionTradeParamsResolved): EditableOptionTradeParams => ({
          tradeId: t.trade_id,
          tradeIdStr: t.trade_id_str,
          ccyPair: t.ccy_pair,
          optionType: t.option_type,
          direction: t.direction,
          strike: t.strike,
          notional1: t.notional1,
          expiryDate: t.expiry_date,
          remainingMaturityYears: t.remaining_maturity_years,
          // Convert decimals → display percentages
          rfRateBase: t.rf_rate_base != null ? t.rf_rate_base * 100 : null,
          rfRateQuote: t.rf_rate_quote != null ? t.rf_rate_quote * 100 : null,
          spot: t.spot,
          volatility: t.volatility != null ? t.volatility * 100 : null,
          curveResolved: t.curve_resolved,
          curveDate: t.curve_date,
          rfRateBaseEdited: false,
          rfRateQuoteEdited: false,
          spotEdited: false,
          volatilityEdited: false,
        }),
      )
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '参数解析失败'
      tradeParams.value = []
    } finally {
      resolving.value = false
    }
  }

  /** Update a single field for an option trade (user edit). Marks the field
   * as user-edited so it is sent as an override (curve-resolved fields that
   * the user did not touch are NOT sent back, letting the backend resolve
   * them from the curve at each relevant date). */
  function updateTradeParam(
    tradeId: number,
    field: 'rfRateBase' | 'rfRateQuote' | 'spot' | 'volatility',
    value: number | null,
  ) {
    const idx = tradeParams.value.findIndex((t) => t.tradeId === tradeId)
    if (idx === -1) return
    const editedKey = `${field}Edited` as keyof Pick<
      EditableOptionTradeParams,
      'rfRateBaseEdited' | 'rfRateQuoteEdited' | 'spotEdited' | 'volatilityEdited'
    >
    tradeParams.value[idx] = {
      ...tradeParams.value[idx],
      [field]: value,
      [editedKey]: true,
    }
  }

  /** Build user-edit overrides from tradeParams. Only fields the user
   * explicitly edited are sent (with display values converted back to
   * decimals); unedited curve-resolved fields are left null so the backend
   * resolves them from the curve at each relevant date. */
  function buildOverrides(): OptionTradeParamsOverride[] {
    return tradeParams.value
      .filter(
        (tp) =>
          tp.rfRateBaseEdited ||
          tp.rfRateQuoteEdited ||
          tp.spotEdited ||
          tp.volatilityEdited,
      )
      .map((tp) => ({
        trade_id: tp.tradeId,
        rf_rate_base: tp.rfRateBaseEdited && tp.rfRateBase != null ? tp.rfRateBase / 100 : null,
        rf_rate_quote: tp.rfRateQuoteEdited && tp.rfRateQuote != null ? tp.rfRateQuote / 100 : null,
        spot: tp.spotEdited ? tp.spot : null,
        volatility: tp.volatilityEdited && tp.volatility != null ? tp.volatility / 100 : null,
      }))
  }

  /** Build the request and call the greeks endpoint. */
  async function calculate(portfolioId: number) {
    loading.value = true
    error.value = null
    try {
      const validationError = validateTradeParams()
      if (validationError) {
        error.value = validationError
        return
      }

      const overrides: OptionTradeParamsOverride[] = buildOverrides()

      const request: PortfolioGreeksRequest = {
        valuation_date: valuationDate.value,
        curve_type: curveType.value,
        trade_params: overrides,
      }
      result.value = await fetchPortfolioGreeks(portfolioId, request)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Greeks 计算失败'
      result.value = null
    } finally {
      loading.value = false
    }
  }

  /** Build the request and call the aggregated analysis endpoint. */
  async function calculateAggregated(portfolioIds: number[]) {
    if (portfolioIds.length === 0) return

    loading.value = true
    error.value = null
    try {
      const validationError = validateTradeParams()
      if (validationError) {
        error.value = validationError
        return
      }

      const overrides: OptionTradeParamsOverride[] = buildOverrides()

      const request: AggregatedAnalysisRequest = {
        portfolio_ids: portfolioIds,
        start_date: startDate.value,
        valuation_date: valuationDate.value,
        curve_type: curveType.value,
        trade_params: overrides,
      }
      aggregatedResult.value = await fetchAggregatedGreeks(request)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '聚合分析计算失败'
      aggregatedResult.value = null
    } finally {
      loading.value = false
    }
  }

  return {
    // state
    valuationDate,
    startDate,
    curveType,
    selectedPortfolioIds,
    tradeParams,
    result,
    aggregatedResult,
    loading,
    resolving,
    error,
    // actions
    resolveParams,
    updateTradeParam,
    calculate,
    calculateAggregated,
    resetResult,
    resetTradeParams,
  }
}
