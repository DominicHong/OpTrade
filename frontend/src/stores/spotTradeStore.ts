import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  SpotTrade,
  SpotTradeCreate,
  SpotTradeFilterParams,
  SpotTradeUpdate,
} from '@/types/spotTrade'
import {
  fetchSpotTrades,
  fetchSpotTrade,
  createSpotTrade as apiCreateSpotTrade,
  updateSpotTrade as apiUpdateSpotTrade,
  deleteSpotTrade as apiDeleteSpotTrade,
  batchDeleteSpotTrades as apiBatchDelete,
} from '@/api/spotTrades'

export const useSpotTradeStore = defineStore('spotTrade', () => {
  const trades = ref<SpotTrade[]>([])
  const currentTrade = ref<SpotTrade | null>(null)
  const totalCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Current filters
  const filters = ref<SpotTradeFilterParams>({
    page: 1,
    page_size: 50,
    sort_by: 'trade_date',
    sort_order: 'desc',
  })

  async function loadTrades(params?: SpotTradeFilterParams) {
    loading.value = true
    error.value = null
    try {
      if (params) {
        filters.value = { ...filters.value, ...params }
      }
      const result = await fetchSpotTrades(filters.value)
      trades.value = result.data
      totalCount.value = result.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load spot trades'
    } finally {
      loading.value = false
    }
  }

  async function loadTrade(id: number) {
    loading.value = true
    error.value = null
    try {
      currentTrade.value = await fetchSpotTrade(id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load spot trade'
    } finally {
      loading.value = false
    }
  }

  async function addTrade(payload: SpotTradeCreate) {
    const created = await apiCreateSpotTrade(payload)
    totalCount.value += 1
    return created
  }

  async function saveTrade(id: number, payload: SpotTradeUpdate) {
    const updated = await apiUpdateSpotTrade(id, payload)
    const idx = trades.value.findIndex(t => t.id === id)
    if (idx >= 0) trades.value[idx] = updated
    if (currentTrade.value?.id === id) currentTrade.value = updated
    return updated
  }

  async function removeTrade(id: number) {
    await apiDeleteSpotTrade(id)
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

  function setFilters(newFilters: Partial<SpotTradeFilterParams>) {
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
