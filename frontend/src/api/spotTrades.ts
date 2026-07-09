import apiClient from './client'
import { uploadFile } from './upload'
import type {
  SpotTrade,
  SpotTradeCreate,
  SpotTradeFilterParams,
  SpotTradeListResponse,
  SpotTradeUpdate,
} from '@/types/spotTrade'
import type { ImportConfirmResponse } from '@/types/api'

export async function fetchSpotTrades(
  params: SpotTradeFilterParams = {}
): Promise<SpotTradeListResponse> {
  const { data } = await apiClient.get('/spot-trades', { params })
  return data
}

export async function fetchSpotTrade(id: number): Promise<SpotTrade> {
  const { data } = await apiClient.get(`/spot-trades/${id}`)
  return data
}

export async function createSpotTrade(payload: SpotTradeCreate): Promise<SpotTrade> {
  const { data } = await apiClient.post('/spot-trades', payload)
  return data
}

export async function updateSpotTrade(
  id: number,
  payload: SpotTradeUpdate
): Promise<SpotTrade> {
  const { data } = await apiClient.put(`/spot-trades/${id}`, payload)
  return data
}

export async function deleteSpotTrade(id: number): Promise<void> {
  await apiClient.delete(`/spot-trades/${id}`)
}

export async function batchDeleteSpotTrades(
  ids: number[]
): Promise<{ status: string; count: string }> {
  const { data } = await apiClient.post('/spot-trades/batch-delete', { ids })
  return data
}

export async function uploadSpotFile(file: File): Promise<ImportConfirmResponse> {
  return uploadFile<ImportConfirmResponse>('/imports/spot/upload', file)
}

export async function getSpotColumnMapping(): Promise<{
  mapping: Record<string, string>
  total_columns: number
}> {
  const { data } = await apiClient.get('/imports/spot/columns')
  return data
}
