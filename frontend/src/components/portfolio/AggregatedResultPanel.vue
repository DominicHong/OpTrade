<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AggregatedAnalysisResponse } from '@/types/portfolio'
import { toWan } from '@/utils/format'

const props = defineProps<{
  result: AggregatedAnalysisResponse
}>()

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

// --- Option detail pagination ---
const optionPage = ref(1)
const optionPageSize = 10
const optionTotalPages = computed(() =>
  Math.max(1, Math.ceil(props.result.option_trades.length / optionPageSize))
)
const pagedOptionTrades = computed(() => {
  const start = (optionPage.value - 1) * optionPageSize
  return props.result.option_trades.slice(start, start + optionPageSize)
})

// --- Spot detail pagination ---
const spotPage = ref(1)
const spotPageSize = 10
const spotTotalPages = computed(() =>
  Math.max(1, Math.ceil(props.result.spot_trades.length / spotPageSize))
)
const pagedSpotTrades = computed(() => {
  const start = (spotPage.value - 1) * spotPageSize
  return props.result.spot_trades.slice(start, start + spotPageSize)
})

function exerciseStatusClass(status: string | null | undefined): string {
  if (!status) return ''
  if (status === '已行权') return 'status-exercised'
  if (status === '未行权') return 'status-unexercised'
  return 'status-unexpired'
}
</script>

<template>
  <!-- ================================================================ -->
  <!-- Summary Cards                                                    -->
  <!-- ================================================================ -->
  <div class="card">
    <h3>{{ result.portfolio_name }} — 风险指标</h3>

    <!-- Option risk indicators -->
    <h4 class="section-label">期权风险指标</h4>
    <div class="greeks-summary">
      <div class="greek-card greek-delta">
        <span class="greek-label">Delta (加权, 万)</span>
        <span class="greek-value">{{ fmt(toWan(result.summary.total_delta), 2) }}</span>
      </div>
      <div class="greek-card greek-gamma">
        <span class="greek-label">Gamma (加权, 万)</span>
        <span class="greek-value">{{ fmt(toWan(result.summary.total_gamma), 2) }}</span>
      </div>
      <div class="greek-card greek-npv">
        <span class="greek-label">NPV (加权, 万)</span>
        <span class="greek-value">{{ fmt(toWan(result.summary.total_npv), 2) }}</span>
      </div>
      <div class="greek-card greek-profit">
        <span class="greek-label">期权费损益 (万)</span>
        <span class="greek-value" :class="profitColor(result.summary.total_option_premium_pnl)">
          {{ fmt(toWan(result.summary.total_option_premium_pnl), 2) }}
        </span>
      </div>
      <div class="greek-card greek-profit">
        <span class="greek-label">期权行权损益 (万)</span>
        <span class="greek-value" :class="profitColor(result.summary.total_option_exercise_pnl)">
          {{ fmt(toWan(result.summary.total_option_exercise_pnl), 2) }}
        </span>
      </div>
      <div class="greek-card greek-profit">
        <span class="greek-label">期权总损益 (万)</span>
        <span class="greek-value" :class="profitColor(result.summary.total_option_pnl)">
          {{ fmt(toWan(result.summary.total_option_pnl), 2) }}
        </span>
      </div>
    </div>

    <!-- Spot P&L section (reserved for future risk indicators) -->
    <h4 class="section-label">即期</h4>
    <div class="greeks-summary">
      <div class="greek-card greek-profit">
        <span class="greek-label">即期损益 (万)</span>
        <span class="greek-value" :class="profitColor(result.summary.total_spot_pnl)">
          {{ fmt(toWan(result.summary.total_spot_pnl), 2) }}
        </span>
      </div>
      <!-- Reserved for future spot risk indicators -->
    </div>

    <!-- Aggregate summary -->
    <h4 class="section-label">汇总</h4>
    <div class="greeks-summary">
      <div class="greek-card greek-profit">
        <span class="greek-label">总损益 (万)</span>
        <span class="greek-value" :class="profitColor(result.summary.total_pnl)">
          {{ fmt(toWan(result.summary.total_pnl), 2) }}
        </span>
      </div>
    </div>

    <!-- Meta info -->
    <div class="meta-row">
      <span>投组数: {{ result.portfolio_count }}</span>
      <span>期权交易: {{ result.option_trade_count }} 笔</span>
      <span>即期交易: {{ result.spot_trade_count }} 笔</span>
      <span v-if="result.start_date">起始日: {{ fmtDate(result.start_date) }}</span>
      <span v-if="result.valuation_date">估值日: {{ fmtDate(result.valuation_date) }}</span>
    </div>
  </div>

  <!-- ================================================================ -->
  <!-- Option Detail Table                                               -->
  <!-- ================================================================ -->
  <div v-if="result.option_trades.length > 0" class="card">
    <h3>期权明细 ({{ result.option_trades.length }} 笔)</h3>
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
            <th>期权费损益(万)</th>
            <th>行权损益(万)</th>
            <th>总损益(万)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in pagedOptionTrades" :key="'opt-' + t.trade_id" :class="{ 'row-error': t.error }">
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
          </tr>
          <tr v-for="t in pagedOptionTrades" :key="'opterr-' + t.trade_id" class="error-row-detail" v-show="t.error">
            <td colspan="16" class="error-inline">{{ t.error }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Option pagination -->
    <div v-if="optionTotalPages > 1" class="pagination">
      <button class="page-btn" :disabled="optionPage <= 1" @click="optionPage = 1">«</button>
      <button class="page-btn" :disabled="optionPage <= 1" @click="optionPage--">‹</button>
      <span class="page-info">{{ optionPage }} / {{ optionTotalPages }}</span>
      <button class="page-btn" :disabled="optionPage >= optionTotalPages" @click="optionPage++">›</button>
      <button class="page-btn" :disabled="optionPage >= optionTotalPages" @click="optionPage = optionTotalPages">»</button>
    </div>
  </div>

  <!-- ================================================================ -->
  <!-- Spot Detail Table                                                 -->
  <!-- ================================================================ -->
  <div v-if="result.spot_trades.length > 0" class="card">
    <h3>即期明细 ({{ result.spot_trades.length }} 笔)</h3>
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
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in pagedSpotTrades" :key="'spot-' + t.trade_id" :class="{ 'row-error': t.error }">
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
          </tr>
          <tr v-for="t in pagedSpotTrades" :key="'spterr-' + t.trade_id" class="error-row-detail" v-show="t.error">
            <td colspan="11" class="error-inline">{{ t.error }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Spot pagination -->
    <div v-if="spotTotalPages > 1" class="pagination">
      <button class="page-btn" :disabled="spotPage <= 1" @click="spotPage = 1">«</button>
      <button class="page-btn" :disabled="spotPage <= 1" @click="spotPage--">‹</button>
      <span class="page-info">{{ spotPage }} / {{ spotTotalPages }}</span>
      <button class="page-btn" :disabled="spotPage >= spotTotalPages" @click="spotPage++">›</button>
      <button class="page-btn" :disabled="spotPage >= spotTotalPages" @click="spotPage = spotTotalPages">»</button>
    </div>
  </div>

  <!-- No data -->
  <div v-if="result.option_trades.length === 0 && result.spot_trades.length === 0" class="card">
    <p class="placeholder-text">所选投资组合在指定日期区间内无交易数据。</p>
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

.section-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0.75rem 0 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--color-border);
}

.greeks-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.25rem;
}
.greek-card {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.65rem 0.85rem;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
}
.greek-label {
  font-size: 0.675rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
}
.greek-value {
  font-size: 1.05rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.greek-delta .greek-value { color: #2563eb; }
.greek-gamma .greek-value { color: #7c3aed; }
.greek-npv .greek-value { color: #059669; }
.greek-profit .greek-value { color: #059669; }
.profit-positive { color: #059669; }
.profit-negative { color: #ef4444; }

.meta-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

/* ---- Detail tables ---- */
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
.row-error { color: var(--color-text-secondary); }
.error-inline { color: #ef4444; font-size: 0.7rem; font-style: italic; }

/* ---- Badges ---- */
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

/* ---- Pagination ---- */
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

.placeholder-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; }
</style>
