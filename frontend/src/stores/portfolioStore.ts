import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Portfolio } from '@/types/portfolio'
import { fetchPortfolios, fetchPortfolio, createPortfolio, updatePortfolio, deletePortfolio } from '@/api/portfolios'

export const usePortfolioStore = defineStore('portfolio', () => {
  const portfolios = ref<Portfolio[]>([])
  const currentPortfolio = ref<Portfolio | null>(null)
  const selectedPortfolioIds = ref<number[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadPortfolios() {
    loading.value = true
    error.value = null
    try {
      portfolios.value = await fetchPortfolios()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load portfolios'
    } finally {
      loading.value = false
    }
  }

  async function loadPortfolio(id: number) {
    currentPortfolio.value = await fetchPortfolio(id)
  }

  async function addPortfolio(name: string, description?: string) {
    const p = await createPortfolio({ name, description })
    portfolios.value.push(p)
    return p
  }

  async function savePortfolio(id: number, data: { name?: string | null; description?: string | null }) {
    const updated = await updatePortfolio(id, data)
    const idx = portfolios.value.findIndex(p => p.id === id)
    if (idx !== -1) portfolios.value[idx] = updated
    if (currentPortfolio.value?.id === id) currentPortfolio.value = updated
    return updated
  }

  async function removePortfolio(id: number) {
    await deletePortfolio(id)
    portfolios.value = portfolios.value.filter(p => p.id !== id)
    if (currentPortfolio.value?.id === id) currentPortfolio.value = null
    // Remove from multi-select if present
    const selIdx = selectedPortfolioIds.value.indexOf(id)
    if (selIdx >= 0) selectedPortfolioIds.value.splice(selIdx, 1)
  }

  function togglePortfolioSelection(id: number) {
    const idx = selectedPortfolioIds.value.indexOf(id)
    if (idx >= 0) {
      selectedPortfolioIds.value.splice(idx, 1)
    } else {
      selectedPortfolioIds.value.push(id)
    }
  }

  function selectAllPortfolios() {
    if (selectedPortfolioIds.value.length === portfolios.value.length) {
      selectedPortfolioIds.value = []
    } else {
      selectedPortfolioIds.value = portfolios.value.map((p) => p.id)
    }
  }

  function clearPortfolioSelection() {
    selectedPortfolioIds.value = []
  }

  return {
    portfolios, currentPortfolio, selectedPortfolioIds, loading, error,
    loadPortfolios, loadPortfolio, addPortfolio, savePortfolio, removePortfolio,
    togglePortfolioSelection, selectAllPortfolios, clearPortfolioSelection,
  }
})
