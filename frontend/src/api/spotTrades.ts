import apiClient from './client'
import { createCrudApi } from './_crud'
import { uploadFile } from './upload'
import type {
  SpotTrade,
  SpotTradeCreate,
  SpotTradeFilterParams,
  SpotTradeListResponse,
  SpotTradeUpdate,
} from '@/types/spotTrade'
import type { ImportConfirmResponse } from '@/types/api'

const crud = createCrudApi<
  SpotTrade,
  SpotTradeCreate,
  SpotTradeUpdate,
  SpotTradeFilterParams,
  SpotTradeListResponse
>('/spot-trades')

export const fetchSpotTrades = crud.fetchList
export const fetchSpotTrade = crud.fetchOne
export const createSpotTrade = crud.create
export const updateSpotTrade = crud.update
export const deleteSpotTrade = crud.remove
export const batchDeleteSpotTrades = crud.batchDelete

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
