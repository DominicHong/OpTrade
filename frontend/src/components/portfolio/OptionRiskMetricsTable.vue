<script setup lang="ts">
import { computed } from 'vue'
import type { CcyPairOptionMetrics } from '@/types/portfolio'
import { toWan } from '@/utils/format'

const props = defineProps<{
  metrics: CcyPairOptionMetrics[]
}>()

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val == null) return '—'
  return val.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function fmtGreek(val: number | null | undefined, decimals = 2): string {
  if (val == null) return '—'
  return val.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function profitColor(val: number | null | undefined): string {
  if (val == null) return ''
  if (val > 0) return 'profit-positive'
  if (val < 0) return 'profit-negative'
  return ''
}

// Zero-value filter: hide pairs where ALL 6 indicators (after toWan scaling)
// are within ±0.0001 in 万 units (i.e. ±1 in original currency units).
const FILTER_THRESHOLD = 0.0001

function shouldHide(m: CcyPairOptionMetrics): boolean {
  const values = [
    toWan(m.npv_cny),
    toWan(m.premium_pnl_cny),
    toWan(m.exercise_pnl_cny),
    toWan(m.total_option_pnl_cny),
    toWan(m.delta),
    toWan(m.gamma),
  ]
  return values.every((v) => v != null && Math.abs(v as number) <= FILTER_THRESHOLD)
}

const visibleMetrics = computed(() =>
  (props.metrics ?? []).filter((m) => !shouldHide(m)),
)

// Summary row — only sum the CNY P&L items (NOT Delta/Gamma, which are
// in original currency and cannot be meaningfully summed across pairs).
const summary = computed(() => {
  const items = visibleMetrics.value
  return {
    npv_cny: items.reduce((s, m) => s + (m.npv_cny || 0), 0),
    premium_pnl_cny: items.reduce((s, m) => s + (m.premium_pnl_cny || 0), 0),
    exercise_pnl_cny: items.reduce((s, m) => s + (m.exercise_pnl_cny || 0), 0),
    total_option_pnl_cny: items.reduce((s, m) => s + (m.total_option_pnl_cny || 0), 0),
    pair_count: items.length,
    hidden_count: (props.metrics?.length ?? 0) - items.length,
  }
})
</script>

<template>
  <div v-if="visibleMetrics.length > 0" class="metrics-table-wrap">
    <table class="metrics-table">
      <thead>
        <tr>
          <th class="col-pair">货币对</th>
          <th class="col-rate" title="该货币对 ccy2 → CNY 的折算汇率">汇率→CNY</th>
          <th>NPV (CNY, 万)</th>
          <th>估值损益 (CNY, 万)</th>
          <th>行权损益 (CNY, 万)</th>
          <th>期权总损益 (CNY, 万)</th>
          <th title="原币 (ccy2/1ccy1) 单位，未折算 CNY">Delta (原币)</th>
          <th title="原币 (ccy2/1ccy1) 单位，未折算 CNY">Gamma (原币)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in visibleMetrics" :key="m.ccy_pair">
          <td class="col-pair">{{ m.ccy_pair }}</td>
          <td class="col-rate">
            {{ m.fx_rate_to_cny != null ? fmt(m.fx_rate_to_cny, 4) : '—' }}
          </td>
          <td>{{ fmt(toWan(m.npv_cny)) }}</td>
          <td :class="profitColor(m.premium_pnl_cny)">{{ fmt(toWan(m.premium_pnl_cny)) }}</td>
          <td :class="profitColor(m.exercise_pnl_cny)">
            {{ fmt(toWan(m.exercise_pnl_cny)) }}
          </td>
          <td :class="profitColor(m.total_option_pnl_cny)">
            {{ fmt(toWan(m.total_option_pnl_cny)) }}
          </td>
          <td>{{ fmtGreek(m.delta) }}</td>
          <td>{{ fmtGreek(m.gamma) }}</td>
        </tr>
        <!-- Summary row -->
        <tr class="summary-row">
          <td class="col-pair">
            汇总
            <span class="summary-meta">({{ summary.pair_count }} 对)</span>
          </td>
          <td class="col-rate">—</td>
          <td>{{ fmt(toWan(summary.npv_cny)) }}</td>
          <td :class="profitColor(summary.premium_pnl_cny)">
            {{ fmt(toWan(summary.premium_pnl_cny)) }}
          </td>
          <td :class="profitColor(summary.exercise_pnl_cny)">
            {{ fmt(toWan(summary.exercise_pnl_cny)) }}
          </td>
          <td :class="profitColor(summary.total_option_pnl_cny)">
            {{ fmt(toWan(summary.total_option_pnl_cny)) }}
          </td>
          <td class="col-na">—</td>
          <td class="col-na">—</td>
        </tr>
      </tbody>
    </table>
    <p v-if="summary.hidden_count > 0" class="hidden-hint">
      已隐藏 {{ summary.hidden_count }} 个全零货币对（所有指标在「万」单位下 ≤ ±0.0001）
    </p>
  </div>
  <div v-else class="empty-state">
    <p>暂无期权风险指标数据（所有货币对均为零值或无数据）</p>
  </div>
</template>

<style scoped>
.metrics-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
}
.metrics-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.metrics-table th,
.metrics-table td {
  padding: 0.55rem 0.7rem;
  text-align: right;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.metrics-table th {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  background: var(--color-bg-surface, var(--color-surface));
  position: sticky;
  top: 0;
}
.metrics-table td:first-child,
.metrics-table th:first-child { text-align: left; }
.col-pair {
  font-weight: 600;
  color: var(--color-text);
}
.col-rate {
  color: var(--color-text-secondary);
  font-size: 0.75rem;
}
.col-na {
  color: var(--color-text-secondary);
}
.summary-row {
  background: var(--color-bg-surface, var(--color-surface));
  font-weight: 700;
  border-top: 2px solid var(--color-primary);
}
.summary-row td {
  border-bottom: none;
}
.summary-meta {
  font-weight: 400;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  margin-left: 0.25rem;
}
.hidden-hint {
  margin: 0.5rem 0.75rem;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  font-style: italic;
}
.empty-state {
  padding: 1.5rem;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  font-style: italic;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
}
.profit-positive { color: #059669; }
.profit-negative { color: #ef4444; }
</style>
