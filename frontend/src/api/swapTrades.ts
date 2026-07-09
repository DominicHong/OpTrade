import apiClient from './client'
import { createCrudApi } from './_crud'
import { uploadFile } from './upload'
import type {
  SwapTrade,
  SwapTradeCreate,
  SwapTradeFilterParams,
  SwapTradeListResponse,
  SwapTradeUpdate,
} from '@/types/swapTrade'
import type { ImportConfirmResponse } from '@/types/api'

const crud = createCrudApi<
  SwapTrade,
  SwapTradeCreate,
  SwapTradeUpdate,
  SwapTradeFilterParams,
  SwapTradeListResponse
>('/swap-trades')

export const fetchSwapTrades = crud.fetchList
export const fetchSwapTrade = crud.fetchOne
export const createSwapTrade = crud.create
export const updateSwapTrade = crud.update
export const deleteSwapTrade = crud.remove
export const batchDeleteSwapTrades = crud.batchDelete

export async function uploadSwapFile(file: File): Promise<ImportConfirmResponse> {
  return uploadFile<ImportConfirmResponse>('/imports/swap/upload', file)
}

export async function getSwapColumnMapping(): Promise<{
  mapping: Record<string, string>
  total_columns: number
}> {
  const { data } = await apiClient.get('/imports/swap/columns')
  return data
}
