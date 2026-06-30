import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { OptionTrade, OptionTradeCreate, OptionTradeFilterParams, OptionTradeUpdate } from '@/types/optionTrade'
import { fetchOptionTrades, fetchOptionTrade, createOptionTrade as apiCreateOptionTrade, updateOptionTrade as apiUpdateOptionTrade, deleteOptionTrade as apiDeleteOptionTrade, batchDeleteOptionTrades as apiBatchDelete } from '@/api/optionTrades'

export const useOptionTradeStore = defineStore('optionTrade', () => {
  const trades = ref<OptionTrade[]>([])
  const currentTrade = ref<OptionTrade | null>(null)
  const totalCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Current filters
  const filters = ref<OptionTradeFilterParams>({
    page: 1,
    page_size: 50,
    sort_by: 'trade_id',
    sort_order: 'asc',
  })

  async function loadTrades(params?: OptionTradeFilterParams) {
    loading.value = true
    error.value = null
    try {
      if (params) {
        filters.value = { ...filters.value, ...params }
      }
      const result = await fetchOptionTrades(filters.value)
      trades.value = result.data
      totalCount.value = result.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load option trades'
    } finally {
      loading.value = false
    }
  }

  async function loadTrade(id: number) {
    loading.value = true
    error.value = null
    try {
      currentTrade.value = await fetchOptionTrade(id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load option trade'
    } finally {
      loading.value = false
    }
  }

  async function addTrade(payload: OptionTradeCreate) {
    const created = await apiCreateOptionTrade(payload)
    totalCount.value += 1
    return created
  }

  async function saveTrade(id: number, payload: OptionTradeUpdate) {
    const updated = await apiUpdateOptionTrade(id, payload)
    const idx = trades.value.findIndex(t => t.id === id)
    if (idx >= 0) trades.value[idx] = updated
    if (currentTrade.value?.id === id) currentTrade.value = updated
    return updated
  }

  async function removeTrade(id: number) {
    await apiDeleteOptionTrade(id)
    trades.value = trades.value.filter(t => t.id !== id)
    totalCount.value -= 1
    if (currentTrade.value?.id === id) currentTrade.value = null
  }

  async function batchDelete(ids: number[]) {
    const result = await apiBatchDelete(ids)
    const deletedCount = parseInt(result.count, 10)
    trades.value = trades.value.filter(t => !ids.includes(t.id))
    totalCount.value -= deletedCount
    if (currentTrade.value && ids.includes(currentTrade.value.id)) currentTrade.value = null
    return deletedCount
  }

  function setPage(page: number) {
    filters.value.page = page
    loadTrades()
  }

  function setFilters(newFilters: Partial<OptionTradeFilterParams>) {
    filters.value = { ...filters.value, ...newFilters, page: 1 }
    loadTrades()
  }

  return {
    trades, currentTrade, totalCount, loading, error, filters,
    loadTrades, loadTrade, addTrade, saveTrade, removeTrade, batchDelete, setPage, setFilters,
  }
})
