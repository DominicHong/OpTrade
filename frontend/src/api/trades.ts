import apiClient from './client'
import type { Trade, TradeCreate, TradeFilterParams, TradeListResponse, TradeUpdate } from '@/types/trade'

export async function fetchTrades(params: TradeFilterParams = {}): Promise<TradeListResponse> {
  const { data } = await apiClient.get('/trades', { params })
  return data
}

export async function fetchTrade(id: number): Promise<Trade> {
  const { data } = await apiClient.get(`/trades/${id}`)
  return data
}

export async function createTrade(payload: TradeCreate): Promise<Trade> {
  const { data } = await apiClient.post('/trades', payload)
  return data
}

export async function updateTrade(id: number, payload: TradeUpdate): Promise<Trade> {
  const { data } = await apiClient.put(`/trades/${id}`, payload)
  return data
}

export async function deleteTrade(id: number): Promise<void> {
  await apiClient.delete(`/trades/${id}`)
}

export async function batchDeleteTrades(ids: number[]): Promise<{ status: string; count: string }> {
  const { data } = await apiClient.post('/trades/batch-delete', { ids })
  return data
}
