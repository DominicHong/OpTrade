import { createCrudApi } from './_crud'
import type { OptionTrade, OptionTradeCreate, OptionTradeFilterParams, OptionTradeListResponse, OptionTradeUpdate } from '@/types/optionTrade'

const crud = createCrudApi<
  OptionTrade,
  OptionTradeCreate,
  OptionTradeUpdate,
  OptionTradeFilterParams,
  OptionTradeListResponse
>('/option-trades')

export const fetchOptionTrades = crud.fetchList
export const fetchOptionTrade = crud.fetchOne
export const createOptionTrade = crud.create
export const updateOptionTrade = crud.update
export const deleteOptionTrade = crud.remove
export const batchDeleteOptionTrades = crud.batchDelete
