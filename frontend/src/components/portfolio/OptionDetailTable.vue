<script setup lang="ts">
import { computed, ref } from 'vue'
import type { OptionTradeAnalysisDetail } from '@/types/portfolio'
import { toWan } from '@/utils/format'

const props = defineProps<{
  trades: OptionTradeAnalysisDetail[]
}>()

const page = ref(1)
const pageSize = 10
const totalPages = computed(() =>
  Math.max(1, Math.ceil(props.trades.length / pageSize)),
)
const pagedTrades = computed(() => {
  const start = (page.value - 1) * pageSize
  return props.trades.slice(start, start + pageSize)
})

function fmt(val: number | null | undefined, decimals = 4): string {
  if (val == null) return '—'
  return val.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function fmtDate(val: string | null | undefined): string {
  if (!val) return '—'
  return val
}

function profitColor(val: number | null | undefined): string {
  if (val == null) return ''
  if (val > 0) return 'profit-positive'
  if (val < 0) return 'profit-negative'
  return ''
}

function isCall(optionType: string | null | undefined): boolean {
  return !!optionType && optionType.toUpperCase() === 'CALL'
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
            <th>交易ID</th>
            <th>货币对</th>
            <th>类型</th>
            <th>方向</th>
            <th>Strike</th>
            <th>Notional(万)</th>
            <th>交易日</th>
            <th>到期日</th>
            <th>行权状态</th>
            <th>Delta</th>
            <th>Gamma</th>
            <th>NPV</th>
            <th>期权费</th>
            <th>估值损益(万)</th>
            <th>行权损益(万)</th>
            <th>总损益(万)</th>
            <th title="原币损益折算 CNY 用的汇率">汇率</th>
            <th>估值损益(CNY,万)</th>
            <th>行权损益(CNY,万)</th>
            <th>总损益(CNY,万)</th>
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
            <td :colspan="20" class="error-inline">{{ t.error }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button class="page-btn" :disabled="page <= 1" @click="page = 1">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="page--">‹</button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="page++">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="page = totalPages">»</button>
    </div>
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
.detail-table td:first-child,
.detail-table th:first-child { text-align: left; }
.detail-table td:nth-child(2),
.detail-table th:nth-child(2) { text-align: left; }
.detail-table td:nth-child(3),
.detail-table th:nth-child(3) { text-align: center; }
.detail-table td:nth-child(4),
.detail-table th:nth-child(4) { text-align: center; }
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

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  margin-top: 0.75rem;
}
.page-btn {
  padding: 0.25rem 0.55rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
  font-size: 0.75rem;
  transition: all var(--transition-fast);
}
.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  padding: 0 0.5rem;
}
.profit-positive { color: #059669; }
.profit-negative { color: #ef4444; }
</style>
