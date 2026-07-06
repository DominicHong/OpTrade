import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  SwapTrade,
  SwapTradeCreate,
  SwapTradeFilterParams,
  SwapTradeUpdate,
} from '@/types/swapTrade'
import {
  fetchSwapTrades,
  fetchSwapTrade,
  createSwapTrade as apiCreateSwapTrade,
  updateSwapTrade as apiUpdateSwapTrade,
  deleteSwapTrade as apiDeleteSwapTrade,
  batchDeleteSwapTrades as apiBatchDelete,
} from '@/api/swapTrades'

export const useSwapTradeStore = defineStore('swapTrade', () => {
  const trades = ref<SwapTrade[]>([])
  const currentTrade = ref<SwapTrade | null>(null)
  const totalCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Current filters
  const filters = ref<SwapTradeFilterParams>({
    page: 1,
    page_size: 50,
    sort_by: 'trade_date',
    sort_order: 'desc',
  })

  async function loadTrades(params?: SwapTradeFilterParams) {
    loading.value = true
    error.value = null
    try {
      if (params) {
        filters.value = { ...filters.value, ...params }
      }
      const result = await fetchSwapTrades(filters.value)
      trades.value = result.data
      totalCount.value = result.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load swap trades'
    } finally {
      loading.value = false
    }
  }

  async function loadTrade(id: number) {
    loading.value = true
    error.value = null
    try {
      currentTrade.value = await fetchSwapTrade(id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load swap trade'
    } finally {
      loading.value = false
    }
  }

  async function addTrade(payload: SwapTradeCreate) {
    const created = await apiCreateSwapTrade(payload)
    totalCount.value += 1
    return created
  }

  async function saveTrade(id: number, payload: SwapTradeUpdate) {
    const updated = await apiUpdateSwapTrade(id, payload)
    const idx = trades.value.findIndex(t => t.id === id)
    if (idx >= 0) trades.value[idx] = updated
    if (currentTrade.value?.id === id) currentTrade.value = updated
    return updated
  }

  async function removeTrade(id: number) {
    await apiDeleteSwapTrade(id)
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

  function setFilters(newFilters: Partial<SwapTradeFilterParams>) {
    filters.value = { ...filters.value, ...newFilters, page: 1 }
    loadTrades()
  }

  return {
    trades,
    currentTrade,
    totalCount,
    loading,
    error,
    filters,
    loadTrades,
    loadTrade,
    addTrade,
    saveTrade,
    removeTrade,
    batchDelete,
    setPage,
    setFilters,
  }
})
