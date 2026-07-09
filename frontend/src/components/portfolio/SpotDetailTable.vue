<script setup lang="ts">
import type { SpotTradeAnalysisDetail } from '@/types/portfolio'
import PaginationControls from '@/components/shared/PaginationControls.vue'
import { useClientPagination } from '@/composables/useClientPagination'
import { fmt, fmtDate, profitColor, toWan } from '@/utils/format'

const props = defineProps<{
  trades: SpotTradeAnalysisDetail[]
}>()

const { page, totalPages, pagedItems: pagedTrades } = useClientPagination(() => props.trades)
</script>

<template>
  <div v-if="trades.length > 0" class="card">
    <h3>即期明细 ({{ trades.length }} 笔)</h3>
    <div class="table-wrap">
      <table class="detail-table">
        <thead>
          <tr>
            <th>交易ID</th>
            <th>货币对</th>
            <th>方向</th>
            <th>类型</th>
            <th>成交价</th>
            <th>Notional(万)</th>
            <th>交易日</th>
            <th>清算日</th>
            <th>市场汇率</th>
            <th>调整成交价</th>
            <th>即期损益(万)</th>
            <th title="原币损益折算 CNY 用的汇率">汇率</th>
            <th>即期损益(CNY,万)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in pagedTrades" :key="'spot-' + t.trade_id" :class="{ 'row-error': t.error }">
            <td>{{ t.trade_id_str ?? t.trade_id }}</td>
            <td>{{ t.ccy_pair ?? '—' }}</td>
            <td>{{ t.direction ?? '—' }}</td>
            <td>
              <span v-if="t.is_derivative" class="badge-derivative">衍生</span>
              <span v-else class="badge-normal">普通</span>
            </td>
            <td>{{ fmt(t.deal_price) }}</td>
            <td>{{ fmt(toWan(t.notional), 2) }}</td>
            <td>{{ fmtDate(t.trade_date) }}</td>
            <td>{{ fmtDate(t.settlement_date) }}</td>
            <td>{{ fmt(t.market_rate) }}</td>
            <td>{{ fmt(t.adjusted_deal_price) }}</td>
            <td :class="profitColor(t.pnl)">{{ t.error ? '—' : fmt(toWan(t.pnl), 2) }}</td>
            <td class="col-rate">{{ t.fx_rate_to_cny != null ? fmt(t.fx_rate_to_cny, 4) : '—' }}</td>
            <td :class="profitColor(t.pnl_cny)">{{ t.error ? '—' : fmt(toWan(t.pnl_cny), 2) }}</td>
          </tr>
          <tr v-for="t in pagedTrades" :key="'spterr-' + t.trade_id" class="error-row-detail" v-show="t.error">
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

.badge-derivative {
  background: #fce7f3;
  color: #9d174d;
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
.badge-normal {
  background: #f1f5f9;
  color: #64748b;
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 0.675rem;
  font-weight: 600;
}
</style>
