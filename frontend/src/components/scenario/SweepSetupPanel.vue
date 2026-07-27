<script setup lang="ts">
import { watch } from 'vue'
import { SWEEP_VARIABLE_LABELS } from '@/types/scenario'

const props = defineProps<{
  modelPair: string | null
  modelVariable: string
  modelMin: number
  modelMax: number
  modelSteps: number
  pairs: string[]
  loading: boolean
  initialized: boolean
}>()

const emit = defineEmits<{
  'update:modelPair': [value: string | null]
  'update:modelVariable': [value: string]
  'update:modelMin': [value: number]
  'update:modelMax': [value: number]
  'update:modelSteps': [value: number]
  run: []
}>()

watch(() => props.pairs, (pairs) => {
  if (!props.modelPair && pairs.length > 0) {
    emit('update:modelPair', pairs[0])
  }
}, { immediate: true })
</script>

<template>
  <div class="card">
    <h3>货币对情景设置</h3>
    <p class="section-desc">
      选择货币对和待分析变量，设置取值范围后点击「自定义分析」。
      系统将在该范围内等步长扫描，其余变量保持不变。
    </p>

    <div v-if="!initialized" class="hint">
      请先在上方选择投资组合并点击「初始化」。
    </div>

    <div v-else class="sweep-form">
      <div class="param-row">
        <div class="param-field">
          <label for="sweep-pair">货币对</label>
          <select
            id="sweep-pair"
            :value="modelPair"
            @change="emit('update:modelPair', ($event.target as HTMLSelectElement).value || null)"
          >
            <option v-for="p in pairs" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="param-field">
          <label for="sweep-var">变化变量</label>
          <select
            id="sweep-var"
            :value="modelVariable"
            @change="emit('update:modelVariable', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="(label, key) in SWEEP_VARIABLE_LABELS" :key="key" :value="key">
              {{ label }}
            </option>
          </select>
        </div>
      </div>

      <div class="param-row">
        <div class="param-field">
          <label for="sweep-min">最小值</label>
          <input
            id="sweep-min"
            type="number"
            :value="modelMin"
            step="any"
            @input="emit('update:modelMin', parseFloat(($event.target as HTMLInputElement).value) || 0)"
          />
        </div>
        <div class="param-field">
          <label for="sweep-max">最大值</label>
          <input
            id="sweep-max"
            type="number"
            :value="modelMax"
            step="any"
            @input="emit('update:modelMax', parseFloat(($event.target as HTMLInputElement).value) || 0)"
          />
        </div>
        <div class="param-field">
          <label for="sweep-steps">步数</label>
          <input
            id="sweep-steps"
            type="number"
            :value="modelSteps"
            min="2"
            max="100"
            @input="emit('update:modelSteps', parseInt(($event.target as HTMLInputElement).value) || 20)"
          />
        </div>
        <div class="param-field param-action">
          <label>&nbsp;</label>
          <button
            class="btn-sweep"
            :disabled="loading || !modelPair"
            @click="emit('run')"
          >
            {{ loading ? '计算中...' : '自定义分析' }}
          </button>
        </div>
      </div>
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
.card h3 {
  font-size: 0.9375rem;
  margin-bottom: 0.4rem;
}
.section-desc {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.85rem;
}
.hint {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-style: italic;
  padding: 0.5rem 0;
}
.sweep-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.param-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}
.param-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 120px;
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
.btn-sweep {
  padding: 0.45rem 0.9rem;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--transition-fast);
}
.btn-sweep:hover:not(:disabled) { filter: brightness(1.1); }
.btn-sweep:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
