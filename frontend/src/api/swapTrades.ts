import apiClient from './client'
import type {
  SwapTrade,
  SwapTradeCreate,
  SwapTradeFilterParams,
  SwapTradeListResponse,
  SwapTradeUpdate,
} from '@/types/swapTrade'
import type { ImportConfirmResponse } from '@/types/api'

export async function fetchSwapTrades(
  params: SwapTradeFilterParams = {}
): Promise<SwapTradeListResponse> {
  const { data } = await apiClient.get('/swap-trades', { params })
  return data
}

export async function fetchSwapTrade(id: number): Promise<SwapTrade> {
  const { data } = await apiClient.get(`/swap-trades/${id}`)
  return data
}

export async function createSwapTrade(payload: SwapTradeCreate): Promise<SwapTrade> {
  const { data } = await apiClient.post('/swap-trades', payload)
  return data
}

export async function updateSwapTrade(
  id: number,
  payload: SwapTradeUpdate
): Promise<SwapTrade> {
  const { data } = await apiClient.put(`/swap-trades/${id}`, payload)
  return data
}

export async function deleteSwapTrade(id: number): Promise<void> {
  await apiClient.delete(`/swap-trades/${id}`)
}

export async function batchDeleteSwapTrades(
  ids: number[]
): Promise<{ status: string; count: string }> {
  const { data } = await apiClient.post('/swap-trades/batch-delete', { ids })
  return data
}

export async function uploadSwapFile(file: File): Promise<ImportConfirmResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/imports/swap/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

export async function getSwapColumnMapping(): Promise<{
  mapping: Record<string, string>
  total_columns: number
}> {
  const { data } = await apiClient.get('/imports/swap/columns')
  return data
}
