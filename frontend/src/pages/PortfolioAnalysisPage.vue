<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useCurveStore } from '@/stores/curveStore'
import { useGreeksCalculation } from '@/composables/useGreeksCalculation'
import PortfolioSelector from '@/components/portfolio/PortfolioSelector.vue'
import GreeksParamsForm from '@/components/portfolio/GreeksParamsForm.vue'
import GreeksResultPanel from '@/components/portfolio/GreeksResultPanel.vue'
import GreeksHelpPanel from '@/components/portfolio/GreeksHelpPanel.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'

const pfStore = usePortfolioStore()
const curveStore = useCurveStore()
const {
  valuationDate,
  curveType,
  tradeParams,
  result,
  loading,
  resolving,
  error,
  resolveParams,
  updateTradeParam,
  calculate,
  resetResult,
  resetTradeParams,
} = useGreeksCalculation()

onMounted(async () => {
  await Promise.all([
    pfStore.loadPortfolios(),
    curveStore.init(),
  ])
})

// Reset when portfolio changes
watch(() => pfStore.currentPortfolio, () => {
  resetResult()
  resetTradeParams()
})

async function onResolveParams() {
  if (!pfStore.currentPortfolio) return
  await resolveParams(pfStore.currentPortfolio.id)
}

async function onCalculate() {
  if (!pfStore.currentPortfolio) return
  await calculate(pfStore.currentPortfolio.id)
}
</script>

<template>
  <div class="portfolio-page">
    <div class="page-header">
      <h1>组合分析</h1>
      <p class="page-desc">选择投资组合，使用参考曲线推导参数，查看聚合风险指标</p>
    </div>

    <div v-if="pfStore.loading"><LoadingSpinner message="加载组合..." /></div>

    <template v-else>
      <PortfolioSelector
        :portfolios="pfStore.portfolios"
        :current-portfolio="pfStore.currentPortfolio"
        :loading="pfStore.loading"
        @select="pfStore.loadPortfolio"
      />

      <GreeksParamsForm
        v-if="pfStore.currentPortfolio"
        :valuation-date="valuationDate"
        :curve-type="curveType"
        :trade-params="tradeParams"
        :curve-definitions="curveStore.definitions"
        :loading="loading"
        :resolving="resolving"
        @update:valuation-date="valuationDate = $event"
        @update:curve-type="curveType = $event"
        @resolve-params="onResolveParams"
        @update-trade-param="(tradeId: number, field: any, value: number | null) => updateTradeParam(tradeId, field, value)"
        @submit="onCalculate"
      />

      <div v-if="error" class="card card-error">
        <p class="error-text">{{ error }}</p>
      </div>

      <GreeksResultPanel v-if="result" :result="result" />

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
