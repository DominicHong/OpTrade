<script setup lang="ts">
import type { GreeksParams } from '@/composables/useGreeksCalculation'

defineProps<{
  params: GreeksParams
  loading: boolean
}>()

const emit = defineEmits<{
  submit: []
}>()
</script>

<template>
  <div class="card">
    <h3>计算参数</h3>
    <div class="params-grid">
      <div class="param-field">
        <label for="valuation-date">估值日期</label>
        <input id="valuation-date" type="date" v-model="params.valuationDate" />
      </div>
      <div class="param-field">
        <label for="rf-rate-base">Base 货币无风险利率 (%)</label>
        <input id="rf-rate-base" type="number" step="0.1" v-model.number="params.rfRateBase" placeholder="3" />
      </div>
      <div class="param-field">
        <label for="rf-rate-quote">Quote 货币无风险利率 (%)</label>
        <input id="rf-rate-quote" type="number" step="0.1" v-model.number="params.rfRateQuote" placeholder="3" />
      </div>
      <div class="param-field">
        <label for="volatility">波动率 (%)</label>
        <input id="volatility" type="number" step="0.1" v-model.number="params.volatility" placeholder="如 1，留空则使用交易自带波动率" />
      </div>
      <div class="param-field">
        <label for="spot">即期汇率</label>
        <input id="spot" type="number" step="0.0001" v-model.number="params.spot" placeholder="留空则使用交易自带即期" />
      </div>
    </div>
    <button class="btn-calc" @click="emit('submit')" :disabled="loading">
      {{ loading ? '计算中...' : '计算 Greeks' }}
    </button>
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
.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
.param-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.param-field label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}
.param-field input {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.param-field input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}
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
</style>
