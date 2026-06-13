import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Trade, TradeCreate, TradeFilterParams, TradeUpdate } from '@/types/trade'
import { fetchTrades, fetchTrade, createTrade as apiCreateTrade, updateTrade as apiUpdateTrade, deleteTrade as apiDeleteTrade } from '@/api/trades'

export const useTradeStore = defineStore('trade', () => {
  const trades = ref<Trade[]>([])
  const currentTrade = ref<Trade | null>(null)
  const totalCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Current filters
  const filters = ref<TradeFilterParams>({
    page: 1,
    page_size: 50,
    sort_by: 'trade_id',
    sort_order: 'asc',
  })

  async function loadTrades(params?: TradeFilterParams) {
    loading.value = true
    error.value = null
    try {
      if (params) {
        filters.value = { ...filters.value, ...params }
      }
      const result = await fetchTrades(filters.value)
      trades.value = result.data
      totalCount.value = result.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load trades'
    } finally {
      loading.value = false
    }
  }

  async function loadTrade(id: number) {
    loading.value = true
    error.value = null
    try {
      currentTrade.value = await fetchTrade(id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load trade'
    } finally {
      loading.value = false
    }
  }

  async function addTrade(payload: TradeCreate) {
    const created = await apiCreateTrade(payload)
    totalCount.value += 1
    return created
  }

  async function saveTrade(id: number, payload: TradeUpdate) {
    const updated = await apiUpdateTrade(id, payload)
    const idx = trades.value.findIndex(t => t.id === id)
    if (idx >= 0) trades.value[idx] = updated
    if (currentTrade.value?.id === id) currentTrade.value = updated
    return updated
  }

  async function removeTrade(id: number) {
    await apiDeleteTrade(id)
    trades.value = trades.value.filter(t => t.id !== id)
    totalCount.value -= 1
    if (currentTrade.value?.id === id) currentTrade.value = null
  }

  function setPage(page: number) {
    filters.value.page = page
    loadTrades()
  }

  function setFilters(newFilters: Partial<TradeFilterParams>) {
    filters.value = { ...filters.value, ...newFilters, page: 1 }
    loadTrades()
  }

  return {
    trades, currentTrade, totalCount, loading, error, filters,
    loadTrades, loadTrade, addTrade, saveTrade, removeTrade, setPage, setFilters,
  }
})
