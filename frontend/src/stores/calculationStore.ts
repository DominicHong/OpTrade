import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GreeksResult, HeatmapResponse } from '@/types/calculation'
import { calculateGreeks as apiCalculateGreeks } from '@/api/calculations'
import { runHeatmap as apiRunHeatmap } from '@/api/scenarios'

export const useCalculationStore = defineStore('calculation', () => {
  const greeksResults = ref<GreeksResult[]>([])
  const heatmapData = ref<HeatmapResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function calculateGreeks(tradeIds: number[], spot?: number, vol?: number, rate?: number) {
    loading.value = true
    error.value = null
    try {
      greeksResults.value = await apiCalculateGreeks({
        trade_ids: tradeIds,
        spot,
        volatility: vol,
        risk_free_rate: rate,
      })
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Greeks calculation failed'
    } finally {
      loading.value = false
    }
  }

  async function runHeatmap(params: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      heatmapData.value = await apiRunHeatmap(params)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Heatmap calculation failed'
    } finally {
      loading.value = false
    }
  }

  return {
    greeksResults, heatmapData, loading, error,
    calculateGreeks, runHeatmap,
  }
})
