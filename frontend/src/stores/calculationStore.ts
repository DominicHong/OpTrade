import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GreeksResult } from '@/types/calculation'
import { calculateGreeks as apiCalculateGreeks } from '@/api/calculations'

export const useCalculationStore = defineStore('calculation', () => {
  const greeksResults = ref<GreeksResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function calculateGreeks(tradeIds: number[], spot?: number, vol?: number, rfRateBase?: number, rfRateQuote?: number) {
    loading.value = true
    error.value = null
    try {
      greeksResults.value = await apiCalculateGreeks({
        trade_ids: tradeIds,
        spot,
        volatility: vol,
        rf_rate_base: rfRateBase,
        rf_rate_quote: rfRateQuote,
      })
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Greeks calculation failed'
    } finally {
      loading.value = false
    }
  }

  return {
    greeksResults, loading, error,
    calculateGreeks,
  }
})
