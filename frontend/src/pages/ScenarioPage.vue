<script setup lang="ts">
import { ref } from 'vue'
import { DEFAULT_SPOT_SHIFTS, DEFAULT_VOL_SHIFTS, DEFAULT_TIME_HORIZONS } from '@/utils/constants'
import { useCalculationStore } from '@/stores/calculationStore'
import { usePortfolioStore } from '@/stores/portfolioStore'

const calcStore = useCalculationStore()
const pfStore = usePortfolioStore()

const spotShifts = ref<number[]>(DEFAULT_SPOT_SHIFTS)
const volShifts = ref<number[]>(DEFAULT_VOL_SHIFTS)
const timeHorizons = ref<number[]>(DEFAULT_TIME_HORIZONS)
const baseSpot = ref<number>(6.79)
const baseVol = ref<number>(0.014)
const riskFreeRate = ref<number>(0.03)
const valuationDate = ref(new Date().toISOString().slice(0, 10))

async function runHeatmap() {
  // TODO: connect to backend in Phase 4
  await calcStore.runHeatmap({
    portfolio_id: pfStore.currentPortfolio?.id,
    spot_shifts: spotShifts.value,
    vol_shifts: volShifts.value,
    base_spot: baseSpot.value,
    base_vol: baseVol.value,
    risk_free_rate: riskFreeRate.value,
    valuation_date: valuationDate.value,
  })
}
</script>

<template>
  <div class="scenario-page">
    <div class="page-header">
      <h1>情景分析</h1>
      <p class="page-desc">分析标的汇率和波动率变动对组合估值的影响</p>
    </div>

    <!-- Parameters -->
    <div class="card params-card">
      <h3>参数设置</h3>
      <div class="param-grid">
        <div class="param">
          <label>估值日期</label>
          <input type="date" v-model="valuationDate" />
        </div>
        <div class="param">
          <label>标的汇率 (Spot)</label>
          <input type="number" v-model.number="baseSpot" step="0.01" />
        </div>
        <div class="param">
          <label>波动率 (Vol)</label>
          <input type="number" v-model.number="baseVol" step="0.001" />
        </div>
        <div class="param">
          <label>无风险利率</label>
          <input type="number" v-model.number="riskFreeRate" step="0.001" />
        </div>
        <div class="param">
          <label>标的偏移 (bps)</label>
          <input type="text" :value="spotShifts.join(', ')" readonly class="readonly" />
        </div>
        <div class="param">
          <label>波动率偏移 (abs)</label>
          <input type="text" :value="volShifts.join(', ')" readonly class="readonly" />
        </div>
        <div class="param">
          <label>时间跨度 (天)</label>
          <input type="text" :value="timeHorizons.join(', ')" readonly class="readonly" />
        </div>
      </div>

      <button class="btn-primary" @click="runHeatmap" :disabled="calcStore.loading">
        <svg v-if="!calcStore.loading" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        {{ calcStore.loading ? '计算中...' : 'Run Heatmap' }}
      </button>
    </div>

    <!-- Placeholder for heatmap -->
    <div class="card heatmap-placeholder">
      <h3>Spot × Vol Heatmap</h3>
      <div class="placeholder-content">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="placeholder-icon"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        <p class="placeholder-text">
          情景分析 Heatmap 将在 Phase 4 实现。届时此处将展示交互式二维热力图，
          横轴为标的汇率偏移，纵轴为波动率偏移，颜色表示组合 NPV 变化。
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
.card h3 { font-size: 0.9375rem; margin-bottom: 0.85rem; }
.param-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.25rem; }
.param label {
  display: block;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.35rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.param input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}
.param input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}
.param input.readonly {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  cursor: default;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.heatmap-placeholder { text-align: center; }
.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 0;
}
.placeholder-icon { color: var(--color-primary-lighter); }
.placeholder-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; max-width: 500px; }
</style>
