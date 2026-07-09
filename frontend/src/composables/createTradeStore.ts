import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'

/** API surface expected by createTradeStore. */
interface CrudApi<T, C, U, F> {
  fetchList(params?: F): Promise<{ data: T[]; total: number }>
  fetchOne(id: number): Promise<T>
  create(payload: C): Promise<T>
  update(id: number, payload: U): Promise<T>
  remove(id: number): Promise<void>
  batchDelete(ids: number[]): Promise<{ status: string; count: string }>
}

/** Minimum filter shape for a trade store. */
interface TradeFilters {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

/** Build a Pinia setup store for a trade entity.
 *
 * The three trade stores (option/spot/swap) are structurally identical:
 * same state (trades, currentTrade, totalCount, loading, error, filters)
 * and same actions (loadTrades, loadTrade, addTrade, saveTrade, removeTrade,
 * batchDelete, setPage, setFilters).  Only the types, store id, default
 * filters and fallback messages differ.
 */
export function createTradeStore<
  T extends { id: number },
  C,
  U,
  F extends TradeFilters,
>(
  id: string,
  api: CrudApi<T, C, U, F>,
  defaultFilters: F,
  fallbackMsgs: { load: string; loadOne: string },
) {
  return defineStore(id, () => {
    const trades = shallowRef<T[]>([])
    const currentTrade = shallowRef<T | null>(null)
    const totalCount = ref(0)
    const loading = ref(false)
    const error = ref<string | null>(null)
    const filters = ref<F>({ ...defaultFilters })

    async function loadTrades(params?: F) {
      loading.value = true
      error.value = null
      try {
        if (params) filters.value = { ...filters.value, ...params }
        const result = await api.fetchList(filters.value)
        trades.value = result.data
        totalCount.value = result.total
      } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : fallbackMsgs.load
      } finally {
        loading.value = false
      }
    }

    async function loadTrade(id: number) {
      loading.value = true
      error.value = null
      try {
        currentTrade.value = await api.fetchOne(id)
      } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : fallbackMsgs.loadOne
      } finally {
        loading.value = false
      }
    }

    async function addTrade(payload: C) {
      const created = await api.create(payload)
      totalCount.value += 1
      return created
    }

    async function saveTrade(id: number, payload: U) {
      const updated = await api.update(id, payload)
      trades.value = trades.value.map((t) => (t.id === id ? updated : t))
      if (currentTrade.value?.id === id) currentTrade.value = updated
      return updated
    }

    async function removeTrade(id: number) {
      await api.remove(id)
      trades.value = trades.value.filter((t) => t.id !== id)
      totalCount.value -= 1
      if (currentTrade.value?.id === id) currentTrade.value = null
    }

    async function batchDelete(ids: number[]) {
      const result = await api.batchDelete(ids)
      const deletedCount = parseInt(result.count, 10)
      trades.value = trades.value.filter((t) => !ids.includes(t.id))
      totalCount.value -= deletedCount
      if (currentTrade.value && ids.includes(currentTrade.value.id)) currentTrade.value = null
      return deletedCount
    }

    function setPage(page: number) {
      filters.value.page = page
      loadTrades()
    }

    function setFilters(newFilters: Partial<F>) {
      filters.value = { ...filters.value, ...newFilters, page: 1 }
      loadTrades()
    }

    return {
      trades, currentTrade, totalCount, loading, error, filters,
      loadTrades, loadTrade, addTrade, saveTrade, removeTrade, batchDelete, setPage, setFilters,
    }
  })
}
