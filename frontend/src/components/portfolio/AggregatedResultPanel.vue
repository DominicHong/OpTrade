<script setup lang="ts">
import type { AggregatedAnalysisResponse } from '@/types/portfolio'
import OptionRiskMetricsTable from './OptionRiskMetricsTable.vue'
import PortfolioPnlSummary from './PortfolioPnlSummary.vue'
import CurrencyExposureGrid from './CurrencyExposureGrid.vue'
import OptionDetailTable from './OptionDetailTable.vue'
import SpotDetailTable from './SpotDetailTable.vue'
import SwapDetailTable from './SwapDetailTable.vue'

const props = defineProps<{
  result: AggregatedAnalysisResponse
}>()

function fmtDate(val: string | null | undefined): string {
  if (!val) return '—'
  return val
}

const hasAnyTrade = (): boolean =>
  props.result.option_trades.length > 0
  || props.result.spot_trades.length > 0
  || props.result.swap_trades.length > 0
</script>

<template>
  <!-- ================================================================ -->
  <!-- Risk Metrics Summary (3 sections)                                 -->
  <!-- ================================================================ -->
  <div class="card">
    <h3>{{ result.portfolio_name }} — 风险指标</h3>

    <!-- (1) Option risk metrics per currency pair -->
    <h4 class="section-label">期权风险指标 (按货币对)</h4>
    <OptionRiskMetricsTable :metrics="result.summary.option_metrics_by_ccy_pair" />

    <!-- (2) Portfolio P&L summary -->
    <h4 class="section-label">组合损益指标</h4>
    <PortfolioPnlSummary
      :total-option-pnl-cny="result.summary.total_option_pnl_cny"
      :total-spot-pnl-cny="result.summary.total_spot_pnl_cny"
      :total-swap-pnl-cny="result.summary.total_swap_pnl_cny"
      :total-pnl-cny="result.summary.total_pnl_cny"
    />

    <!-- (3) Spot currency exposures -->
    <h4 class="section-label">即期各币种敞口</h4>
    <CurrencyExposureGrid :exposures="result.summary.currency_exposures" />

    <!-- Meta info -->
    <div class="meta-row">
      <span>投组数: {{ result.portfolio_count }}</span>
      <span>期权交易: {{ result.option_trade_count }} 笔</span>
      <span>即期交易: {{ result.spot_trade_count }} 笔</span>
      <span>掉期交易: {{ result.swap_trade_count }} 笔</span>
      <span v-if="result.start_date">起始日: {{ fmtDate(result.start_date) }}</span>
      <span v-if="result.valuation_date">估值日: {{ fmtDate(result.valuation_date) }}</span>
    </div>
  </div>

  <!-- ================================================================ -->
  <!-- Trade Detail Tables (delegated to subcomponents)                  -->
  <!-- ================================================================ -->
  <OptionDetailTable :trades="result.option_trades" />
  <SpotDetailTable :trades="result.spot_trades" />
  <SwapDetailTable :trades="result.swap_trades" />

  <!-- No data -->
  <div v-if="!hasAnyTrade()" class="card">
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

.meta-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

.placeholder-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-style: italic;
}
</style>
