<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useCurveStore } from '@/stores/curveStore'
import { useGreeksCalculation } from '@/composables/useGreeksCalculation'
import { fetchEarliestTradeDate } from '@/api/portfolios'
import PortfolioSelector from '@/components/portfolio/PortfolioSelector.vue'
import GreeksParamsForm from '@/components/portfolio/GreeksParamsForm.vue'
import GreeksResultPanel from '@/components/portfolio/GreeksResultPanel.vue'
import AggregatedResultPanel from '@/components/portfolio/AggregatedResultPanel.vue'
import GreeksHelpPanel from '@/components/portfolio/GreeksHelpPanel.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'

const pfStore = usePortfolioStore()
const curveStore = useCurveStore()
const {
  valuationDate,
  startDate,
  curveType,
  tradeParams,
  result,
  aggregatedResult,
  loading,
  resolving,
  error,
  resolveParams,
  updateTradeParam,
  calculate,
  calculateAggregated,
  resetResult,
  resetTradeParams,
} = useGreeksCalculation()

onMounted(async () => {
  await Promise.all([
    pfStore.loadPortfolios(),
    curveStore.init(),
  ])
  // Default: select first portfolio
  if (pfStore.selectedPortfolioIds.length === 0 && pfStore.portfolios.length > 0) {
    pfStore.togglePortfolioSelection(pfStore.portfolios[0].id)
  }
  // Set default start date from earliest trade date
  await updateStartDateFromSelection()
})

// When selection changes: reset results & update default start date
watch(() => pfStore.selectedPortfolioIds, async () => {
  resetResult()
  resetTradeParams()
  await updateStartDateFromSelection()
}, { deep: true })

async function updateStartDateFromSelection() {
  if (pfStore.selectedPortfolioIds.length === 0) return
  try {
    const earliest = await fetchEarliestTradeDate(pfStore.selectedPortfolioIds)
    if (earliest) {
      startDate.value = earliest
    }
  } catch {
    // Silently ignore — user can pick manually
  }
}

async function onResolveParams() {
  if (pfStore.selectedPortfolioIds.length === 0) return
  // Resolve params for each selected portfolio and merge
  resolving.value = true
  error.value = null
  try {
    const { resolvePortfolioParams } = await import('@/api/portfolios')
    const allTrades: typeof tradeParams.value = []
    for (const pid of pfStore.selectedPortfolioIds) {
      const response = await resolvePortfolioParams(pid, {
        valuation_date: valuationDate.value,
        curve_type: curveType.value || 'fx_implied_rate',
      })
      const mapped = response.trades.map((t) => ({
        tradeId: t.trade_id,
        tradeIdStr: t.trade_id_str,
        ccyPair: t.ccy_pair,
        optionType: t.option_type,
        direction: t.direction,
        strike: t.strike,
        notional1: t.notional1,
        expiryDate: t.expiry_date,
        remainingMaturityYears: t.remaining_maturity_years,
        rfRateBase: t.rf_rate_base != null ? t.rf_rate_base * 100 : null,
        rfRateQuote: t.rf_rate_quote != null ? t.rf_rate_quote * 100 : null,
        spot: t.spot,
        volatility: t.volatility != null ? t.volatility * 100 : null,
        curveResolved: t.curve_resolved,
        curveDate: t.curve_date,
      }))
      allTrades.push(...mapped)
    }
    tradeParams.value = allTrades
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '参数解析失败'
    tradeParams.value = []
  } finally {
    resolving.value = false
  }
}

async function onCalculate() {
  if (pfStore.selectedPortfolioIds.length === 0) return
  await calculateAggregated(pfStore.selectedPortfolioIds)
}
</script>

<template>
  <div class="portfolio-page">
    <div class="page-header">
      <h1>组合分析</h1>
      <p class="page-desc">多投资组合汇总分析，选择投组、设定日期区间，查看期权与即期损益</p>
    </div>

    <div v-if="pfStore.loading"><LoadingSpinner message="加载组合..." /></div>

    <template v-else>
      <PortfolioSelector
        :portfolios="pfStore.portfolios"
        :selected-ids="pfStore.selectedPortfolioIds"
        :loading="pfStore.loading"
        @toggle="pfStore.togglePortfolioSelection"
        @select-all="pfStore.selectAllPortfolios"
      />

      <GreeksParamsForm
        v-if="pfStore.selectedPortfolioIds.length > 0"
        :valuation-date="valuationDate"
        :start-date="startDate"
        :curve-type="curveType"
        :trade-params="tradeParams"
        :curve-definitions="curveStore.definitions"
        :loading="loading"
        :resolving="resolving"
        @update:valuation-date="valuationDate = $event"
        @update:start-date="startDate = $event"
        @update:curve-type="curveType = $event"
        @resolve-params="onResolveParams"
        @update-trade-param="(tradeId: number, field: any, value: number | null) => updateTradeParam(tradeId, field, value)"
        @submit="onCalculate"
      />

      <div v-if="error" class="card card-error">
        <p class="error-text">{{ error }}</p>
      </div>

      <AggregatedResultPanel v-if="aggregatedResult" :result="aggregatedResult" />

      <GreeksHelpPanel />
    </template>
  </div>
</template>

<style scoped>
.portfolio-page { padding: 1rem; }
.page-header { margin-bottom: 1.5rem; }
.page-desc { color: var(--color-text-secondary); font-size: 0.875rem; margin-top: 0.25rem; }
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.card-error { border-color: #ef4444; }
.error-text { color: #ef4444; font-size: 0.8125rem; }
</style>
