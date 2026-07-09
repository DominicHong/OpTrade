import { createTradeStore } from '@/composables/createTradeStore'
import type { OptionTrade, OptionTradeCreate, OptionTradeFilterParams, OptionTradeUpdate } from '@/types/optionTrade'
import {
  batchDeleteOptionTrades,
  createOptionTrade,
  deleteOptionTrade,
  fetchOptionTrade,
  fetchOptionTrades,
  updateOptionTrade,
} from '@/api/optionTrades'

export const useOptionTradeStore = createTradeStore<
  OptionTrade,
  OptionTradeCreate,
  OptionTradeUpdate,
  OptionTradeFilterParams
>(
  'optionTrade',
  {
    fetchList: fetchOptionTrades,
    fetchOne: fetchOptionTrade,
    create: createOptionTrade,
    update: updateOptionTrade,
    remove: deleteOptionTrade,
    batchDelete: batchDeleteOptionTrades,
  },
  { page: 1, page_size: 50, sort_by: 'trade_id', sort_order: 'asc' },
  { load: 'Failed to load option trades', loadOne: 'Failed to load option trade' },
)
