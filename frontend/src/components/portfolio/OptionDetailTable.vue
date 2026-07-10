<script setup lang="ts">
import type { OptionTradeAnalysisDetail } from '@/types/portfolio'
import PaginationControls from '@/components/shared/PaginationControls.vue'
import { useClientPagination } from '@/composables/useClientPagination'
import { useClientSort, type SortColumn } from '@/composables/useClientSort'
import { fmt, fmtDate, isCall, profitColor, toWan } from '@/utils/format'

const props = defineProps<{
  trades: OptionTradeAnalysisDetail[]
}>()

const columns: SortColumn[] = [
  { key: 'trade_id', label: '交易ID', sortable: true, type: 'number' },
  { key: 'ccy_pair', label: '货币对', sortable: true, type: 'string' },
  { key: 'option_type', label: '类型', sortable: true, type: 'string' },
  { key: 'direction', label: '方向', sortable: true, type: 'string' },
  { key: 'strike', label: 'Strike', sortable: true, type: 'number' },
  { key: 'notional1', label: 'Notional(万)', sortable: true, type: 'number' },
  { key: 'trade_date', label: '交易日', sortable: true, type: 'date' },
  { key: 'expiry_date', label: '到期日', sortable: true, type: 'date' },
  { key: 'exercise_status', label: '行权状态', sortable: true, type: 'string' },
  { key: 'delta', label: 'Delta', sortable: true, type: 'number' },
  { key: 'gamma', label: 'Gamma', sortable: true, type: 'number' },
  { key: 'theta', label: 'Theta', sortable: true, type: 'number' },
  { key: 'vega', label: 'Vega', sortable: true, type: 'number' },
  { key: 'npv', label: 'NPV', sortable: true, type: 'number' },
  { key: 'premium', label: '期权费', sortable: true, type: 'number' },
  { key: 'premium_pnl', label: '估值损益(万)', sortable: true, type: 'number' },
  { key: 'exercise_pnl', label: '行权损益(万)', sortable: true, type: 'number' },
  { key: 'total_pnl', label: '总损益(万)', sortable: true, type: 'number' },
  { key: 'fx_rate_to_cny', label: '汇率', sortable: true, type: 'number' },
  { key: 'premium_pnl_cny', label: '估值损益(CNY,万)', sortable: true, type: 'number' },
  { key: 'exercise_pnl_cny', label: '行权损益(CNY,万)', sortable: true, type: 'number' },
  { key: 'total_pnl_cny', label: '总损益(CNY,万)', sortable: true, type: 'number' },
]

const { sortBy, sortOrder, sortedItems, toggleSort } = useClientSort<OptionTradeAnalysisDetail>({
  items: () => props.trades,
  defaultSortBy: 'expiry_date',
  defaultSortOrder: 'desc',
  getColumnType: key => columns.find(c => c.key === key)?.type,
})

const { page, totalPages, pagedItems: pagedTrades } = useClientPagination(() => sortedItems.value)

function onSort(key: string) {
  toggleSort(key)
  page.value = 1
}

function exerciseStatusClass(status: string | null | undefined): string {
  if (!status) return ''
  if (status === '已行权') return 'status-exercised'
  if (status === '未行权') return 'status-unexercised'
  return 'status-unexpired'
}
</script>

<template>
  <div v-if="trades.length > 0" class="card">
    <h3>期权明细 ({{ trades.length }} 笔)</h3>
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
          <tr v-for="t in pagedTrades" :key="'opt-' + t.trade_id" :class="{ 'row-error': t.error }">
            <td>{{ t.trade_id_str ?? t.trade_id }}</td>
            <td>{{ t.ccy_pair ?? '—' }}</td>
            <td>
              <span v-if="t.option_type" :class="isCall(t.option_type) ? 'badge-call' : 'badge-put'">
                {{ t.option_type }}
              </span>
              <span v-else>—</span>
            </td>
            <td>{{ t.direction ?? '—' }}</td>
            <td>{{ fmt(t.strike) }}</td>
            <td>{{ fmt(toWan(t.notional1), 2) }}</td>
            <td>{{ fmtDate(t.trade_date) }}</td>
            <td>{{ fmtDate(t.expiry_date) }}</td>
            <td>
              <span v-if="t.exercise_status" :class="['status-badge', exerciseStatusClass(t.exercise_status)]">
                {{ t.exercise_status }}
              </span>
              <span v-else>—</span>
            </td>
            <td>{{ t.error ? '—' : fmt(t.delta) }}</td>
            <td>{{ t.error ? '—' : fmt(t.gamma) }}</td>
            <td>{{ t.error ? '—' : fmt(t.theta) }}</td>
            <td>{{ t.error ? '—' : fmt(t.vega) }}</td>
            <td>{{ t.error ? '—' : fmt(t.npv, 4) }}</td>
            <td>{{ t.error ? '—' : fmt(t.premium, 4) }}</td>
            <td :class="profitColor(t.premium_pnl)">{{ t.error ? '—' : fmt(toWan(t.premium_pnl), 2) }}</td>
            <td :class="profitColor(t.exercise_pnl)">{{ t.error ? '—' : (t.exercise_pnl != null ? fmt(toWan(t.exercise_pnl), 2) : '—') }}</td>
            <td :class="profitColor(t.total_pnl)">{{ t.error ? '—' : fmt(toWan(t.total_pnl), 2) }}</td>
            <td class="col-rate">{{ t.fx_rate_to_cny != null ? fmt(t.fx_rate_to_cny, 4) : '—' }}</td>
            <td :class="profitColor(t.premium_pnl_cny)">{{ t.error ? '—' : fmt(toWan(t.premium_pnl_cny), 2) }}</td>
            <td :class="profitColor(t.exercise_pnl_cny)">{{ t.error ? '—' : (t.exercise_pnl_cny != null ? fmt(toWan(t.exercise_pnl_cny), 2) : '—') }}</td>
            <td :class="profitColor(t.total_pnl_cny)">{{ t.error ? '—' : fmt(toWan(t.total_pnl_cny), 2) }}</td>
          </tr>
          <tr v-for="t in pagedTrades" :key="'opterr-' + t.trade_id" class="error-row-detail" v-show="t.error">
            <td :colspan="22" class="error-inline">{{ t.error }}</td>
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
.detail-table td:nth-child(4),
.detail-table th:nth-child(4) { text-align: center; }
.sort-arrow { font-size: 0.625rem; margin-left: 2px; }
.col-rate {
  color: var(--color-text-secondary);
  font-size: 0.7rem;
}
.row-error { color: var(--color-text-secondary); }
.error-inline { color: #ef4444; font-size: 0.7rem; font-style: italic; }

.badge-call {
  background: var(--color-positive-bg);
  color: var(--color-positive);
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
.badge-put {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
.status-badge {
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
.status-exercised {
  background: #fef3c7;
  color: #92400e;
}
.status-unexercised {
  background: #f1f5f9;
  color: #64748b;
}
.status-unexpired {
  background: #dbeafe;
  color: #1e40af;
}
</style>
