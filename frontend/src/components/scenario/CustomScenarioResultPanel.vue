<script setup lang="ts">
import type { ScenarioAnalysisResponse } from '@/types/scenario'
import OptionMetricsBarChart from './OptionMetricsBarChart.vue'
import PortfolioPnlBarChart from './PortfolioPnlBarChart.vue'
import { fmtDate } from '@/utils/format'

defineProps<{
  result: ScenarioAnalysisResponse
  title?: string
}>()
</script>

<template>
  <div class="card">
    <div class="header-row">
      <h3 v-if="title">{{ title }}</h3>
      <h3 v-else>{{ result.scenario_name || '当前情景' }}</h3>
      <div class="meta-row">
        <span>投组数: {{ result.portfolio_count }}</span>
        <span>期权: {{ result.option_trade_count }} 笔</span>
        <span>即期: {{ result.spot_trade_count }} 笔</span>
        <span>掉期: {{ result.swap_trade_count }} 笔</span>
        <span v-if="result.start_date">起始日: {{ fmtDate(result.start_date) }}</span>
        <span v-if="result.valuation_date">估值日: {{ fmtDate(result.valuation_date) }}</span>
      </div>
    </div>

    <!-- Option risk metrics by currency pair -->
    <div v-if="result.summary.option_metrics_by_ccy_pair.length > 0" class="section">
      <h4 class="section-label">期权风险指标 (按货币对)</h4>
      <OptionMetricsBarChart :metrics="result.summary.option_metrics_by_ccy_pair" />
    </div>
    <div v-else class="section empty-section">
      <p class="placeholder-text">无期权交易风险数据。</p>
    </div>

    <!-- Portfolio P&L breakdown -->
    <div class="section">
      <h4 class="section-label">组合损益指标</h4>
      <PortfolioPnlBarChart :summary="result.summary" />
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
.header-row {
  margin-bottom: 0.75rem;
}
.header-row h3 {
  font-size: 0.9375rem;
  margin-bottom: 0.35rem;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
}
.section {
  margin-top: 1rem;
}
.section-label {
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-text);
}
.empty-section {
  text-align: center;
  padding: 1rem;
}
.placeholder-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-style: italic;
}
</style>
