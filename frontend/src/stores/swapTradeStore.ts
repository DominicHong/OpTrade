import { createTradeStore } from '@/composables/createTradeStore'
import type {
  SwapTrade,
  SwapTradeCreate,
  SwapTradeFilterParams,
  SwapTradeUpdate,
} from '@/types/swapTrade'
import {
  batchDeleteSwapTrades,
  createSwapTrade,
  deleteSwapTrade,
  fetchSwapTrade,
  fetchSwapTrades,
  updateSwapTrade,
} from '@/api/swapTrades'

export const useSwapTradeStore = createTradeStore<
  SwapTrade,
  SwapTradeCreate,
  SwapTradeUpdate,
  SwapTradeFilterParams
>(
  'swapTrade',
  {
    fetchList: fetchSwapTrades,
    fetchOne: fetchSwapTrade,
    create: createSwapTrade,
    update: updateSwapTrade,
    remove: deleteSwapTrade,
    batchDelete: batchDeleteSwapTrades,
  },
  { page: 1, page_size: 50, sort_by: 'trade_date', sort_order: 'desc' },
  { load: 'Failed to load swap trades', loadOne: 'Failed to load swap trade' },
)
