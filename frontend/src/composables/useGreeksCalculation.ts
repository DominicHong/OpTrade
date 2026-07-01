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
        }),
      )
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '参数解析失败'
      tradeParams.value = []
    } finally {
      resolving.value = false
    }
  }

  /** Update a single field for an option trade (user edit). */
  function updateTradeParam(
    tradeId: number,
    field: 'rfRateBase' | 'rfRateQuote' | 'spot' | 'volatility',
    value: number | null,
  ) {
    const idx = tradeParams.value.findIndex((t) => t.tradeId === tradeId)
    if (idx === -1) return
    tradeParams.value[idx] = { ...tradeParams.value[idx], [field]: value }
  }

  /** Build the request and call the greeks endpoint. */
  async function calculate(portfolioId: number) {
    loading.value = true
    error.value = null
    try {
      const overrides: OptionTradeParamsOverride[] = tradeParams.value
        .filter((tp) => {
          // Only include trades where the user has provided at least one explicit value
          return (
            tp.rfRateBase != null ||
            tp.rfRateQuote != null ||
            tp.spot != null ||
            tp.volatility != null
          )
        })
        .map((tp) => ({
          trade_id: tp.tradeId,
          // Convert display values back to decimals for rates/vol
          rf_rate_base: tp.rfRateBase != null ? tp.rfRateBase / 100 : null,
          rf_rate_quote: tp.rfRateQuote != null ? tp.rfRateQuote / 100 : null,
          spot: tp.spot,
          volatility: tp.volatility != null ? tp.volatility / 100 : null,
        }))

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
      const overrides: OptionTradeParamsOverride[] = tradeParams.value
        .filter((tp) => {
          return (
            tp.rfRateBase != null ||
            tp.rfRateQuote != null ||
            tp.spot != null ||
            tp.volatility != null
          )
        })
        .map((tp) => ({
          trade_id: tp.tradeId,
          rf_rate_base: tp.rfRateBase != null ? tp.rfRateBase / 100 : null,
          rf_rate_quote: tp.rfRateQuote != null ? tp.rfRateQuote / 100 : null,
          spot: tp.spot,
          volatility: tp.volatility != null ? tp.volatility / 100 : null,
        }))

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
