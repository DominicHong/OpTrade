<script setup lang="ts">
import type { PortfolioGreeksResponse } from '@/types/portfolio'
import { toWan } from '@/utils/format'

defineProps<{
  result: PortfolioGreeksResponse
}>()

function fmt(val: number | null | undefined, decimals = 4): string {
  if (val == null) return '—'
  return val.toFixed(decimals)
}
</script>

<template>
  <div class="card">
    <h3>{{ result.portfolio_name }} — 聚合风险指标</h3>
    <div class="greeks-summary">
      <div class="greek-card greek-delta">
        <span class="greek-label">Delta (加权, 万)</span>
        <span class="greek-value">{{ fmt(toWan(result.total_delta), 2) }}</span>
      </div>
      <div class="greek-card greek-gamma">
        <span class="greek-label">Gamma (加权, 万)</span>
        <span class="greek-value">{{ fmt(toWan(result.total_gamma), 2) }}</span>
      </div>
      <div class="greek-card greek-npv">
        <span class="greek-label">NPV (加权, 万)</span>
        <span class="greek-value">{{ fmt(toWan(result.total_npv), 2) }}</span>
      </div>
    </div>
    <div class="params-used">
      <span>
        参数: base r = {{ result.rf_rate_base != null ? (result.rf_rate_base * 100).toFixed(2) + '%' : '—' }},
        quote r = {{ result.rf_rate_quote != null ? (result.rf_rate_quote * 100).toFixed(2) + '%' : '—' }},
        vol = {{ result.volatility_used != null ? (result.volatility_used * 100).toFixed(2) + '%' : '交易自带' }},
        spot = {{ result.spot_used ?? '交易自带' }}
      </span>
    </div>
  </div>

  <div v-if="result.trades.length > 0" class="card">
    <h3>逐笔明细</h3>
    <div class="table-wrap">
      <table class="greeks-table">
        <thead>
          <tr>
            <th>交易ID</th>
            <th>货币对</th>
            <th>类型</th>
            <th>方向</th>
            <th>Strike</th>
            <th>Notional(万)</th>
            <th>Delta</th>
            <th>Gamma</th>
            <th>NPV</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in result.trades" :key="t.trade_id" :class="{ 'row-error': t.error }">
            <td>{{ t.trade_id_str ?? t.trade_id }}</td>
            <td>{{ t.ccy_pair ?? '—' }}</td>
            <td>{{ t.option_type ?? '—' }}</td>
            <td>{{ t.direction ?? '—' }}</td>
            <td>{{ fmt(t.strike) }}</td>
            <td>{{ fmt(toWan(t.notional1), 2) }}</td>
            <td>{{ t.error ? '—' : fmt(t.delta) }}</td>
            <td>{{ t.error ? '—' : fmt(t.gamma) }}</td>
            <td>{{ t.error ? '—' : fmt(t.npv, 2) }}</td>
          </tr>
          <tr v-for="t in result.trades" :key="'err-' + t.trade_id" class="error-row-detail" v-show="t.error">
            <td colspan="9" class="error-inline">{{ t.error }}</td>
          </tr>
        </tbody>
      </table>
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
.card h3 { font-size: 0.9375rem; margin-bottom: 0.85rem; }
.greeks-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.85rem;
  margin-bottom: 0.75rem;
}
.greek-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
}
.greek-label {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
}
.greek-value {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.greek-delta .greek-value { color: #2563eb; }
.greek-gamma .greek-value { color: #7c3aed; }
.greek-npv .greek-value { color: #059669; }
.params-used {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  font-style: italic;
}
.table-wrap { overflow-x: auto; }
.greeks-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.greeks-table th,
.greeks-table td {
  padding: 0.5rem 0.65rem;
  text-align: right;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.greeks-table th {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  background: var(--color-bg);
}
.greeks-table td:first-child,
.greeks-table th:first-child { text-align: left; }
.row-error { color: var(--color-text-secondary); }
.error-inline { color: #ef4444; font-size: 0.75rem; font-style: italic; }
</style>
