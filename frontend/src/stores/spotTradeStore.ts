import { createTradeStore } from '@/composables/createTradeStore'
import type {
  SpotTrade,
  SpotTradeCreate,
  SpotTradeFilterParams,
  SpotTradeUpdate,
} from '@/types/spotTrade'
import {
  batchDeleteSpotTrades,
  createSpotTrade,
  deleteSpotTrade,
  fetchSpotTrade,
  fetchSpotTrades,
  updateSpotTrade,
} from '@/api/spotTrades'

export const useSpotTradeStore = createTradeStore<
  SpotTrade,
  SpotTradeCreate,
  SpotTradeUpdate,
  SpotTradeFilterParams
>(
  'spotTrade',
  {
    fetchList: fetchSpotTrades,
    fetchOne: fetchSpotTrade,
    create: createSpotTrade,
    update: updateSpotTrade,
    remove: deleteSpotTrade,
    batchDelete: batchDeleteSpotTrades,
  },
  { page: 1, page_size: 50, sort_by: 'trade_date', sort_order: 'desc' },
  { load: 'Failed to load spot trades', loadOne: 'Failed to load spot trade' },
)
