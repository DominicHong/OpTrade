import apiClient from './client'
import type { OptionTrade, OptionTradeCreate, OptionTradeFilterParams, OptionTradeListResponse, OptionTradeUpdate } from '@/types/optionTrade'

export async function fetchOptionTrades(params: OptionTradeFilterParams = {}): Promise<OptionTradeListResponse> {
  const { data } = await apiClient.get('/option-trades', { params })
  return data
}

export async function fetchOptionTrade(id: number): Promise<OptionTrade> {
  const { data } = await apiClient.get(`/option-trades/${id}`)
  return data
}

export async function createOptionTrade(payload: OptionTradeCreate): Promise<OptionTrade> {
  const { data } = await apiClient.post('/option-trades', payload)
  return data
}

export async function updateOptionTrade(id: number, payload: OptionTradeUpdate): Promise<OptionTrade> {
  const { data } = await apiClient.put(`/option-trades/${id}`, payload)
  return data
}

export async function deleteOptionTrade(id: number): Promise<void> {
  await apiClient.delete(`/option-trades/${id}`)
}

export async function batchDeleteOptionTrades(ids: number[]): Promise<{ status: string; count: string }> {
  const { data } = await apiClient.post('/option-trades/batch-delete', { ids })
  return data
}
