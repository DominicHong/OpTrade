<script setup lang="ts">
import type { SwapTradeAnalysisDetail } from '@/types/portfolio'
import PaginationControls from '@/components/shared/PaginationControls.vue'
import { useClientPagination } from '@/composables/useClientPagination'
import { useClientSort, type SortColumn } from '@/composables/useClientSort'
import { fmt, fmtDate, profitColor, toWan } from '@/utils/format'

const props = defineProps<{
  trades: SwapTradeAnalysisDetail[]
}>()

const columns: SortColumn[] = [
  { key: 'trade_id', label: '交易ID', sortable: true, type: 'number' },
  { key: 'ccy_pair', label: '货币对', sortable: true, type: 'string' },
  { key: 'direction', label: '方向', sortable: true, type: 'string' },
  { key: 'near_deal_price', label: '近端价', sortable: true, type: 'number' },
  { key: 'far_deal_price', label: '远端价', sortable: true, type: 'number' },
  { key: 'notional', label: 'Notional(万)', sortable: true, type: 'number' },
  { key: 'near_value_date', label: '近端起息日', sortable: true, type: 'date' },
  { key: 'far_value_date', label: '远端起息日', sortable: true, type: 'date' },
  { key: 'status', label: '状态', sortable: true, type: 'string' },
  { key: 'return_rate', label: '收益率', sortable: true, type: 'number' },
  { key: 'pnl', label: '掉期损益(原币,万)', sortable: true, type: 'number' },
  { key: 'fx_rate_to_cny', label: '汇率', sortable: true, type: 'number' },
  { key: 'pnl_cny', label: '掉期损益(CNY,万)', sortable: true, type: 'number' },
]

const { sortBy, sortOrder, sortedItems, toggleSort } = useClientSort<SwapTradeAnalysisDetail>({
  items: () => props.trades,
  defaultSortBy: 'near_value_date',
  defaultSortOrder: 'desc',
  getColumnType: key => columns.find(c => c.key === key)?.type,
})

const { page, totalPages, pagedItems: pagedTrades } = useClientPagination(() => sortedItems.value)

function onSort(key: string) {
  toggleSort(key)
  page.value = 1
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return '—'
  return val.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + '%'
}

function statusBadgeClass(status: string | null | undefined): string {
  if (status === '到期') return 'badge-matured'
  if (status === '存续') return 'badge-active'
  return 'badge-pending'
}
</script>

<template>
  <div v-if="trades.length > 0" class="card">
    <h3>掉期明细 ({{ trades.length }} 笔)</h3>
    <div class="table-wrap">
      <table class="detail-table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="{
                sortable: col.sortable !== false,
                active: sortBy === col.key,
              }"
              @click="onSort(col.key)"
            >
              {{ col.label }}
              <span v-if="sortBy === col.key" class="sort-arrow">
                {{ sortOrder === 'asc' ? '▲' : '▼' }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in pagedTrades" :key="'swap-' + t.trade_id" :class="{ 'row-error': t.error }">
            <td>{{ t.trade_id_str ?? t.trade_id }}</td>
            <td>{{ t.ccy_pair ?? '—' }}</td>
            <td>{{ t.direction ?? '—' }}</td>
            <td>{{ fmt(t.near_deal_price) }}</td>
            <td>{{ fmt(t.far_deal_price) }}</td>
            <td>{{ fmt(toWan(t.notional), 2) }}</td>
            <td>{{ fmtDate(t.near_value_date) }}</td>
            <td>{{ fmtDate(t.far_value_date) }}</td>
            <td><span :class="statusBadgeClass(t.status)">{{ t.status ?? '—' }}</span></td>
            <td>{{ t.error ? '—' : fmtPct(t.return_rate) }}</td>
            <td :class="profitColor(t.pnl)">{{ t.error ? '—' : fmt(toWan(t.pnl), 2) }}</td>
            <td class="col-rate">{{ t.fx_rate_to_cny != null ? fmt(t.fx_rate_to_cny, 4) : '—' }}</td>
            <td :class="profitColor(t.pnl_cny)">{{ t.error ? '—' : fmt(toWan(t.pnl_cny), 2) }}</td>
          </tr>
          <tr v-for="t in pagedTrades" :key="'swperr-' + t.trade_id" class="error-row-detail" v-show="t.error">
            <td :colspan="13" class="error-inline">{{ t.error }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <PaginationControls v-model:page="page" :total-pages="totalPages" />
  </div>
</template>

<style scoped>
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 0.9375rem; margin-bottom: 0.5rem; }

.table-wrap { overflow-x: auto; }
.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.detail-table th,
.detail-table td {
  padding: 0.4rem 0.5rem;
  text-align: right;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.detail-table th {
  font-size: 0.675rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  background: var(--color-bg);
}
.detail-table th.sortable {
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
}
.detail-table th.sortable:hover {
  background: var(--color-bg-hover, var(--color-bg-surface));
  color: var(--color-text);
}
.detail-table th.active {
  color: var(--color-primary);
  background: var(--color-primary-bg);
}
.detail-table td:first-child,
.detail-table th:first-child { text-align: left; }
.detail-table td:nth-child(2),
.detail-table th:nth-child(2) { text-align: left; }
.detail-table td:nth-child(3),
.detail-table th:nth-child(3) { text-align: center; }
.detail-table td:nth-child(9),
.detail-table th:nth-child(9) { text-align: center; }
.sort-arrow { font-size: 0.625rem; margin-left: 2px; }
.col-rate {
  color: var(--color-text-secondary);
  font-size: 0.7rem;
}
.row-error { color: var(--color-text-secondary); }
.error-inline { color: #ef4444; font-size: 0.7rem; font-style: italic; }

.badge-matured {
  background: #fef3c7;
  color: #92400e;
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
.badge-active {
  background: #dbeafe;
  color: #1e40af;
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
.badge-pending {
  background: #f1f5f9;
  color: #64748b;
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
</style>
