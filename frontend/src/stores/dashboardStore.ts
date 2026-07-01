import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DashboardSummary, DashboardDefaultsResponse } from '@/types/api'
import type { AggregatedAnalysisResponse } from '@/types/portfolio'
import {
  fetchDashboardSummary,
  fetchDashboardAnalysis,
  fetchDashboardDefaults,
} from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  // ---- state ----
  const summary = ref<DashboardSummary | null>(null)
  const defaults = ref<DashboardDefaultsResponse | null>(null)
  const analysisResult = ref<AggregatedAnalysisResponse | null>(null)

  const startDate = ref<string | null>(null)
  const valuationDate = ref<string>(new Date().toISOString().slice(0, 10))
  const curveType = ref<string | null>(null)

  const loading = ref(false)
  const calculated = ref(false)
  const error = ref<string | null>(null)

  // ---- actions ----
  async function loadDefaults() {
    try {
      const d = await fetchDashboardDefaults()
      defaults.value = d
      // Only set if not already user-modified
      if (!startDate.value) {
        startDate.value = d.earliest_trade_date
      }
      if (!curveType.value) {
        curveType.value = d.curve_type
      }
    } catch {
      // Silently ignore — user can pick manually
    }
  }

  async function loadSummary() {
    try {
      summary.value = await fetchDashboardSummary()
    } catch {
      // Silently ignore
    }
  }

  async function calculate() {
    loading.value = true
    error.value = null
    try {
      analysisResult.value = await fetchDashboardAnalysis({
        start_date: startDate.value,
        valuation_date: valuationDate.value,
        curve_type: curveType.value,
      })
      calculated.value = true
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '组合分析计算失败'
    } finally {
      loading.value = false
    }
  }

  async function init() {
    await Promise.all([loadSummary(), loadDefaults()])
    if (!calculated.value) {
      await calculate()
    }
  }

  return {
    // state
    summary,
    defaults,
    analysisResult,
    startDate,
    valuationDate,
    curveType,
    loading,
    calculated,
    error,
    // actions
    loadSummary,
    loadDefaults,
    calculate,
    init,
  }
})
