import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ExchangeRate,
  ExchangeRateCoverageSummary,
  ExchangeRateFilterParams,
  ExchangeRateImportResult,
} from '@/types/exchangeRate'
import {
  fetchExchangeRates,
  fetchExchangeRateCoverage,
  fetchCcyPairs,
  importFromCurve,
  importAllDatesFromCurve,
} from '@/api/exchangeRates'

export const useExchangeRateStore = defineStore('exchangeRate', () => {
  // ---- state ----
  const rates = ref<ExchangeRate[]>([])
  const total = ref(0)
  const coverage = ref<ExchangeRateCoverageSummary | null>(null)
  const ccyPairs = ref<string[]>([])
  const loading = ref(false)
  const importing = ref(false)
  const error = ref<string | null>(null)

  const filters = ref<ExchangeRateFilterParams>({
    page: 1,
    page_size: 50,
    sort_by: 'rate_date',
    sort_order: 'desc',
  })

  // ---- computed ----
  const currentPage = computed(() => filters.value.page ?? 1)
  const pageSize = computed(() => filters.value.page_size ?? 50)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  // ---- actions ----
  async function loadRates(params?: ExchangeRateFilterParams) {
    loading.value = true
    error.value = null
    try {
      const merged = { ...filters.value, ...params }
      filters.value = merged
      const result = await fetchExchangeRates(merged)
      rates.value = result.data
      total.value = result.total
      filters.value.page = result.page
      filters.value.page_size = result.page_size
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载汇率数据失败'
    } finally {
      loading.value = false
    }
  }

  async function loadCoverage() {
    try {
      coverage.value = await fetchExchangeRateCoverage()
    } catch {
      // silently ignore — coverage is supplementary
    }
  }

  async function loadCcyPairs() {
    try {
      ccyPairs.value = await fetchCcyPairs()
    } catch {
      // silently ignore
    }
  }

  function setFilters(p: Partial<ExchangeRateFilterParams>) {
    filters.value = { ...filters.value, ...p, page: 1 }
    return loadRates()
  }

  function setSort(column: string) {
    const current = filters.value.sort_by
    const order = current === column && filters.value.sort_order === 'asc' ? 'desc' : 'asc'
    filters.value = { ...filters.value, sort_by: column, sort_order: order, page: 1 }
    return loadRates()
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages.value) return
    return loadRates({ page })
  }

  async function importForDate(rateDate: string): Promise<ExchangeRateImportResult> {
    importing.value = true
    try {
      const result = await importFromCurve(rateDate)
      await Promise.all([loadRates(), loadCoverage()])
      return result
    } finally {
      importing.value = false
    }
  }

  async function importAllDates(): Promise<ExchangeRateImportResult> {
    importing.value = true
    try {
      const result = await importAllDatesFromCurve()
      await Promise.all([loadRates(), loadCoverage()])
      return result
    } finally {
      importing.value = false
    }
  }

  // ---- init ----
  async function init() {
    await Promise.all([loadCoverage(), loadCcyPairs()])
    if (coverage.value && coverage.value.total_records > 0) {
      await loadRates()
    }
  }

  return {
    // state
    rates,
    total,
    coverage,
    ccyPairs,
    loading,
    importing,
    error,
    filters,
    // computed
    currentPage,
    pageSize,
    totalPages,
    // actions
    loadRates,
    loadCoverage,
    loadCcyPairs,
    setFilters,
    setSort,
    goToPage,
    importForDate,
    importAllDates,
    init,
  }
})
