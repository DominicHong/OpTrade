import { ref, watch } from 'vue'
import {
  analyzeScenario,
  analyzeBuiltinScenarios,
  analyzeSweep,
  fetchRequiredPairs,
  fetchDefaultPairParams,
  fetchEarliestGlobalTradeDate,
} from '@/api/scenarios'
import type {
  CcyPairScenarioOverride,
  ScenarioAnalysisResponse,
  BuiltinScenariosResponse,
  EditablePairScenario,
  ScenarioSweepResponse,
} from '@/types/scenario'
import type { CurveDefinition } from '@/types/curve'
import { useCurveStore } from '@/stores/curveStore'

export function useScenarioAnalysis() {
  const valuationDate = ref<string>(new Date().toISOString().slice(0, 10))
  const startDate = ref<string | null>(null)
  const curveType = ref<string | null>(null)
  const selectedPortfolioIds = ref<number[]>([])

  const requiredPairs = ref<string[]>([])
  const pairParams = ref<Record<string, EditablePairScenario>>({})
  const customResult = ref<ScenarioAnalysisResponse | null>(null)
  const builtinResult = ref<BuiltinScenariosResponse | null>(null)
  const loading = ref(false)
  const builtinLoading = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)

  // Sweep analysis state
  const sweepPair = ref<string | null>(null)
  const sweepVariable = ref<string>('spot')
  const sweepMin = ref<number>(0)
  const sweepMax = ref<number>(10)
  const sweepSteps = ref<number>(20)
  const sweepResult = ref<ScenarioSweepResponse | null>(null)
  const sweepLoading = ref(false)

  // Auto-generate the sweep min/max from the pair's initial values when the
  // user picks a different pair or variable. Display units: spot raw,
  // volatility / rates as percent (5.0 = 5%). Converted back to decimals
  // (0.05 = 5%) in runSweep, which matches the backend override schema.
  function applyDefaultSweepRange() {
    const p = sweepPair.value ? pairParams.value[sweepPair.value] : null
    if (!p) return

    let min: number | null = null
    let max: number | null = null
    const round6 = (v: number): number => Math.round(v * 1e6) / 1e6
    const round2 = (v: number): number => Math.round(v * 100) / 100
    switch (sweepVariable.value) {
      case 'spot':
        if (p.defaultSpot != null) {
          min = round6(p.defaultSpot * 0.995)
          max = round6(p.defaultSpot * 1.005)
        }
        break
      case 'volatility':
        if (p.defaultVol != null) {
          min = round2(p.defaultVol * 100 - 5)
          max = round2(p.defaultVol * 100 + 5)
        }
        break
      case 'rf_rate_base':
        if (p.defaultRfBase != null) {
          min = round2(p.defaultRfBase * 100 - 1)
          max = round2(p.defaultRfBase * 100 + 1)
        }
        break
      case 'rf_rate_quote':
        if (p.defaultRfQuote != null) {
          min = round2(p.defaultRfQuote * 100 - 1)
          max = round2(p.defaultRfQuote * 100 + 1)
        }
        break
    }
    if (min != null && max != null) {
      sweepMin.value = min
      sweepMax.value = max
    }
  }

  watch([sweepPair, sweepVariable], applyDefaultSweepRange)

  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  function resetResults() {
    customResult.value = null
    builtinResult.value = null
    error.value = null
  }

  async function init(portfolioIds: number[]) {
    resetResults()
    selectedPortfolioIds.value = portfolioIds

    const curveStore = useCurveStore()
    try {
      await curveStore.init()
    } catch {
      // curve definitions optional
    }

    if (!curveType.value && curveStore.definitions.length > 0) {
      curveType.value = curveStore.definitions[0].curve_type
    }

    try {
      const earliest = await fetchEarliestGlobalTradeDate()
      if (earliest.earliest_trade_date && !startDate.value) {
        startDate.value = earliest.earliest_trade_date
      }
    } catch {
      // use default
    }

    await loadRequiredPairs()
    await loadDefaultParams()
    applyDefaultSweepRange()
    initialized.value = true
  }

  async function loadRequiredPairs() {
    const ids = selectedPortfolioIds.value.length > 0
      ? selectedPortfolioIds.value.join(',')
      : null
    try {
      const resp = await fetchRequiredPairs(ids, valuationDate.value)
      requiredPairs.value = resp.all_pairs
    } catch {
      requiredPairs.value = []
    }
  }

  async function loadDefaultParams() {
    const params: Record<string, EditablePairScenario> = {}
    for (const pair of requiredPairs.value) {
      try {
        const resp = await fetchDefaultPairParams(
          pair, valuationDate.value, curveType.value,
        )
        params[pair] = {
          ccyPair: pair,
          defaultSpot: resp.spot,
          defaultVol: resp.volatility,
          defaultRfBase: resp.rf_rate_base,
          defaultRfQuote: resp.rf_rate_quote,
          currentSpot: resp.spot,
          currentVol: resp.volatility != null ? resp.volatility * 100 : null,
          currentRfBase: resp.rf_rate_base != null ? resp.rf_rate_base * 100 : null,
          currentRfQuote: resp.rf_rate_quote != null ? resp.rf_rate_quote * 100 : null,
          spotEdited: false,
          volEdited: false,
          rfBaseEdited: false,
          rfQuoteEdited: false,
          curveDate: resp.curve_date,
        }
      } catch {
        params[pair] = createEmptyPairScenario(pair)
      }
    }
    pairParams.value = params
  }

  function createEmptyPairScenario(pair: string): EditablePairScenario {
    return {
      ccyPair: pair,
      defaultSpot: null,
      defaultVol: null,
      defaultRfBase: null,
      defaultRfQuote: null,
      currentSpot: null,
      currentVol: null,
      currentRfBase: null,
      currentRfQuote: null,
      spotEdited: false,
      volEdited: false,
      rfBaseEdited: false,
      rfQuoteEdited: false,
      curveDate: null,
    }
  }

  function applyPairOverride(
    pair: string,
    field: 'spot' | 'volatility' | 'rfRateBase' | 'rfRateQuote',
    value: number | null,
  ) {
    const p = pairParams.value[pair]
    if (!p) return

    const fieldMap = {
      spot: 'currentSpot' as const,
      volatility: 'currentVol' as const,
      rfRateBase: 'currentRfBase' as const,
      rfRateQuote: 'currentRfQuote' as const,
    }
    const editedMap = {
      spot: 'spotEdited' as const,
      volatility: 'volEdited' as const,
      rfRateBase: 'rfBaseEdited' as const,
      rfRateQuote: 'rfQuoteEdited' as const,
    }

    p[fieldMap[field]] = value
    p[editedMap[field]] = true

    debounceRecompute()
  }

  function buildPairOverrides(): CcyPairScenarioOverride[] {
    const overrides: CcyPairScenarioOverride[] = []
    for (const [pair, p] of Object.entries(pairParams.value)) {
      const hasOverride = p.spotEdited || p.volEdited || p.rfBaseEdited || p.rfQuoteEdited
      if (!hasOverride) continue

      const po: CcyPairScenarioOverride = { ccy_pair: pair }
      if (p.spotEdited && p.currentSpot != null) po.spot = p.currentSpot
      if (p.volEdited && p.currentVol != null) po.volatility = p.currentVol / 100
      if (p.rfBaseEdited && p.currentRfBase != null) po.rf_rate_base = p.currentRfBase / 100
      if (p.rfQuoteEdited && p.currentRfQuote != null) po.rf_rate_quote = p.currentRfQuote / 100

      if (po.spot != null || po.volatility != null || po.rf_rate_base != null || po.rf_rate_quote != null) {
        overrides.push(po)
      }
    }
    return overrides
  }

  function debounceRecompute() {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      recompute()
    }, 300)
  }

  async function recompute() {
    if (selectedPortfolioIds.value.length === 0) return

    loading.value = true
    error.value = null
    try {
      const overrides = buildPairOverrides()
      customResult.value = await analyzeScenario({
        portfolio_ids: selectedPortfolioIds.value.length > 0 ? selectedPortfolioIds.value : null,
        start_date: startDate.value,
        valuation_date: valuationDate.value,
        curve_type: curveType.value,
        pair_overrides: overrides,
      })
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '情景分析计算失败'
    } finally {
      loading.value = false
    }
  }

  async function runBuiltin() {
    builtinLoading.value = true
    error.value = null
    try {
      builtinResult.value = await analyzeBuiltinScenarios({
        portfolio_ids: selectedPortfolioIds.value.length > 0 ? selectedPortfolioIds.value : null,
        start_date: startDate.value,
        valuation_date: valuationDate.value,
        curve_type: curveType.value,
      })
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '内置情景计算失败'
    } finally {
      builtinLoading.value = false
    }
  }

  async function runSweep() {
    if (!sweepPair.value) return
    sweepLoading.value = true
    error.value = null
    try {
      const response = await analyzeSweep({
        portfolio_ids: selectedPortfolioIds.value.length > 0 ? selectedPortfolioIds.value : null,
        start_date: startDate.value,
        valuation_date: valuationDate.value,
        curve_type: curveType.value,
        ccy_pair: sweepPair.value,
        variable: sweepVariable.value,
        min_value: sweepVariable.value === 'spot' ? sweepMin.value : sweepMin.value / 100,
        max_value: sweepVariable.value === 'spot' ? sweepMax.value : sweepMax.value / 100,
        num_steps: sweepSteps.value,
      })
      sweepResult.value = response
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '扫描分析计算失败'
    } finally {
      sweepLoading.value = false
    }
  }

  return {
    valuationDate,
    startDate,
    curveType,
    selectedPortfolioIds,
    requiredPairs,
    pairParams,
    customResult,
    builtinResult,
    loading,
    builtinLoading,
    error,
    initialized,
    sweepPair,
    sweepVariable,
    sweepMin,
    sweepMax,
    sweepSteps,
    sweepResult,
    sweepLoading,
    init,
    loadRequiredPairs,
    loadDefaultParams,
    applyPairOverride,
    recompute,
    runBuiltin,
    runSweep,
    resetResults,
  }
}
