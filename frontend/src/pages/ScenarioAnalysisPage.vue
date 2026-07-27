<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useCurveStore } from '@/stores/curveStore'
import { useScenarioAnalysis } from '@/composables/useScenarioAnalysis'
import PortfolioSelector from '@/components/portfolio/PortfolioSelector.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PairScenarioList from '@/components/scenario/PairScenarioList.vue'
import CustomScenarioResultPanel from '@/components/scenario/CustomScenarioResultPanel.vue'
import SweepSetupPanel from '@/components/scenario/SweepSetupPanel.vue'
import SweepResultCharts from '@/components/scenario/SweepResultCharts.vue'
import BuiltinScenariosPanel from '@/components/scenario/BuiltinScenariosPanel.vue'

const portfolioStore = usePortfolioStore()
const curveStore = useCurveStore()
const sc = useScenarioAnalysis()

onMounted(async () => {
  await portfolioStore.loadPortfolios()
  await curveStore.init()
  if (!sc.curveType.value && curveStore.definitions.length > 0) {
    sc.curveType.value = curveStore.definitions[0].curve_type
  }
})

const initLoading = ref(false)

async function handleInit() {
  if (portfolioStore.selectedPortfolioIds.length === 0) {
    sc.error.value = '请至少选择一个投资组合'
    return
  }
  initLoading.value = true
  sc.error.value = null
  try {
    sc.selectedPortfolioIds.value = [...portfolioStore.selectedPortfolioIds]
    await sc.init(sc.selectedPortfolioIds.value)
  } catch (e: unknown) {
    sc.error.value = e instanceof Error ? e.message : '初始化失败'
  } finally {
    initLoading.value = false
  }
}

async function handleRecompute() {
  await sc.recompute()
}

async function handleRunBuiltin() {
  await sc.runBuiltin()
}
</script>

<template>
  <div class="scenario-page">
    <div class="page-header">
      <h1>情景分析</h1>
      <p class="page-desc">
        调整各货币对的即期汇率、波动率、Base利率和Quote利率，
        动态评估组合在自定义情景与系统内置情景下的期权风险指标和损益情况。
      </p>
    </div>

    <!-- A: Portfolio selector + params -->
    <div class="card">
      <h3>选择投组与参数</h3>
      <PortfolioSelector
        :portfolios="portfolioStore.portfolios"
        :selected-ids="portfolioStore.selectedPortfolioIds"
        :loading="false"
        @toggle="portfolioStore.togglePortfolioSelection"
        @select-all="portfolioStore.selectAllPortfolios"
      />

      <div class="common-params">
        <div class="param-field">
          <label for="start-date">起始日</label>
          <input
            id="start-date"
            type="date"
            :value="sc.startDate.value"
            @input="sc.startDate.value = ($event.target as HTMLInputElement).value || null"
          />
        </div>
        <div class="param-field">
          <label for="valuation-date">结束日/估值日</label>
          <input
            id="valuation-date"
            type="date"
            :value="sc.valuationDate.value"
            @input="sc.valuationDate.value = ($event.target as HTMLInputElement).value"
          />
        </div>
        <div class="param-field">
          <label for="curve-type">参考曲线</label>
          <select
            id="curve-type"
            :value="sc.curveType.value"
            @change="sc.curveType.value = ($event.target as HTMLSelectElement).value || null"
          >
            <option
              v-for="def in curveStore.definitions"
              :key="def.id"
              :value="def.curve_type"
            >
              {{ def.name }}
            </option>
          </select>
        </div>
        <div class="param-field param-action">
          <label>&nbsp;</label>
          <button
            class="btn-init"
            :disabled="initLoading"
            @click="handleInit"
          >
            {{ initLoading ? '初始化中...' : '初始化' }}
          </button>
        </div>
      </div>

      <p v-if="sc.error.value && !sc.initialized.value" class="error-text">{{ sc.error.value }}</p>
    </div>

    <!-- B: Sweep setup (show after init) -->
    <SweepSetupPanel
      v-if="sc.initialized.value"
      :model-pair="sc.sweepPair.value"
      :model-variable="sc.sweepVariable.value"
      :model-min="sc.sweepMin.value"
      :model-max="sc.sweepMax.value"
      :model-steps="sc.sweepSteps.value"
      :pairs="sc.requiredPairs.value"
      :loading="sc.sweepLoading.value"
      :initialized="sc.initialized.value"
      @update:model-pair="sc.sweepPair.value = $event"
      @update:model-variable="sc.sweepVariable.value = $event"
      @update:model-min="sc.sweepMin.value = $event"
      @update:model-max="sc.sweepMax.value = $event"
      @update:model-steps="sc.sweepSteps.value = $event"
      @run="sc.runSweep()"
    />

    <!-- C: Sweep results -->
    <LoadingSpinner v-if="sc.sweepLoading.value" message="计算中..." />
    <div v-if="sc.error.value && sc.initialized.value && !sc.sweepLoading.value" class="card error-card">
      <p class="error-text">{{ sc.error.value }}</p>
    </div>
    <SweepResultCharts
      v-if="sc.sweepResult.value && !sc.sweepLoading.value"
      :result="sc.sweepResult.value"
    />

    <!-- D: Builtin scenarios -->
    <div v-if="sc.initialized.value" class="card">
      <h3>系统内置情景</h3>
      <p class="section-desc">
        运行 11 个预置市场情景（基准、波动率冲击、即期汇率冲击、波动率+即期组合冲击），横向对比各情景下的组合损益。
      </p>
      <button
        class="btn-calc"
        :disabled="sc.builtinLoading.value"
        @click="handleRunBuiltin"
      >
        {{ sc.builtinLoading.value ? '计算中...' : '计算内置情景' }}
      </button>
    </div>
    <LoadingSpinner v-if="sc.builtinLoading.value" message="计算内置情景中..." />
    <BuiltinScenariosPanel
      v-if="sc.builtinResult.value && !sc.builtinLoading.value"
      :result="sc.builtinResult.value"
    />
  </div>
</template>

<style scoped>
.scenario-page {
  max-width: 1200px;
}
.page-header {
  margin-bottom: 1.5rem;
}
.page-header h1 {
  font-size: 1.25rem;
}
.page-desc {
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
  margin-top: 0.25rem;
  max-width: 700px;
}
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.card h3 {
  font-size: 0.9375rem;
  margin-bottom: 0.75rem;
}
.section-desc {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
}

/* Common params row */
.common-params {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin-top: 1rem;
  flex-wrap: wrap;
}
.param-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 140px;
}
.param-field label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}
.param-field input,
.param-field select {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.param-field input:focus,
.param-field select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}
.param-action { min-width: auto; }

.btn-init {
  padding: 0.45rem 0.9rem;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
  white-space: nowrap;
}
.btn-init:hover { filter: brightness(1.1); }
.btn-init:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-calc {
  padding: 0.5rem 1.25rem;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.btn-calc:hover { filter: brightness(1.1); }
.btn-calc:disabled { opacity: 0.6; cursor: not-allowed; }

.error-card {
  border-color: var(--color-negative);
  background: var(--color-negative-bg);
}
.error-text {
  color: var(--color-negative);
  font-size: 0.8125rem;
}
</style>
