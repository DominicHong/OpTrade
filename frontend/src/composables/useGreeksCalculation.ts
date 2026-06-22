import { ref } from 'vue'
import { fetchPortfolioGreeks } from '@/api/portfolios'
import type { PortfolioGreeksRequest, PortfolioGreeksResponse } from '@/types/portfolio'

export interface GreeksParams {
  rfRateBase: number
  rfRateQuote: number
  volatility: number | null
  spot: number | null
  valuationDate: string
}

export function useGreeksCalculation() {
  const params = ref<GreeksParams>({
    rfRateBase: 3,
    rfRateQuote: 3,
    volatility: null,
    spot: null,
    valuationDate: new Date().toISOString().slice(0, 10),
  })

  const result = ref<PortfolioGreeksResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function resetResult() {
    result.value = null
    error.value = null
  }

  async function calculate(portfolioId: number) {
    loading.value = true
    error.value = null
    try {
      const request: PortfolioGreeksRequest = {
        rf_rate_base: params.value.rfRateBase / 100,
        rf_rate_quote: params.value.rfRateQuote / 100,
        volatility: params.value.volatility != null ? params.value.volatility / 100 : null,
        spot: params.value.spot,
        valuation_date: params.value.valuationDate,
      }
      result.value = await fetchPortfolioGreeks(portfolioId, request)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Greeks 计算失败'
      result.value = null
    } finally {
      loading.value = false
    }
  }

  return {
    params,
    result,
    loading,
    error,
    calculate,
    resetResult,
  }
}
