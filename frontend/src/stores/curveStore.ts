import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  CurveDefinition,
  CurveCoverageSummary,
  CrawlResult,
  FxImpliedRate,
  FxImpliedRateFilterParams,
} from '@/types/curve'
import {
  fetchCurveDefinitions,
  fetchFxImpliedRates,
  fetchCurveCoverage,
  triggerRefresh,
} from '@/api/curves'

export const useCurveStore = defineStore('curve', () => {
  // ---- state ----
  const definitions = ref<CurveDefinition[]>([])
  const rates = ref<FxImpliedRate[]>([])
  const total = ref(0)
  const coverage = ref<CurveCoverageSummary | null>(null)
  const loading = ref(false)
  const refreshing = ref(false)
  const error = ref<string | null>(null)

  // current filter state
  const filters = ref<FxImpliedRateFilterParams>({
    page: 1,
    page_size: 50,
  })

  // ---- computed ----
  const activeDefinition = computed(() =>
    definitions.value.find((d) => d.curve_type === 'fx_implied_rate'),
  )

  const currentPage = computed(() => filters.value.page ?? 1)
  const pageSize = computed(() => filters.value.page_size ?? 50)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  // ---- actions ----
  async function loadDefinitions() {
    try {
      definitions.value = await fetchCurveDefinitions()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载曲线定义失败'
    }
  }

  async function loadRates(params?: FxImpliedRateFilterParams) {
    loading.value = true
    error.value = null
    try {
      const merged = { ...filters.value, ...params }
      filters.value = merged
      const result = await fetchFxImpliedRates(merged)
      rates.value = result.data
      total.value = result.total
      filters.value.page = result.page
      filters.value.page_size = result.page_size
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载曲线数据失败'
    } finally {
      loading.value = false
    }
  }

  async function loadCoverage() {
    try {
      coverage.value = await fetchCurveCoverage()
    } catch {
      // silently ignore — coverage is supplementary
    }
  }

  function setFilters(p: Partial<FxImpliedRateFilterParams>) {
    filters.value = { ...filters.value, ...p, page: 1 }
    return loadRates()
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages.value) return
    return loadRates({ page })
  }

  async function refresh(): Promise<CrawlResult> {
    refreshing.value = true
    try {
      const result = await triggerRefresh()
      // Reload data after successful refresh
      await Promise.all([loadRates(), loadCoverage()])
      return result
    } finally {
      refreshing.value = false
    }
  }

  // ---- init ----
  async function init() {
    await Promise.all([loadDefinitions(), loadCoverage()])
    if (coverage.value && coverage.value.total_records > 0) {
      await loadRates()
    }
  }

  return {
    // state
    definitions,
    rates,
    total,
    coverage,
    loading,
    refreshing,
    error,
    filters,
    // computed
    activeDefinition,
    currentPage,
    pageSize,
    totalPages,
    // actions
    loadDefinitions,
    loadRates,
    loadCoverage,
    setFilters,
    goToPage,
    refresh,
    init,
  }
})
