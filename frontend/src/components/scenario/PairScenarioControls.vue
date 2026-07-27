<script setup lang="ts">
import { computed } from 'vue'
import type { EditablePairScenario } from '@/types/scenario'

const props = defineProps<{
  pair: EditablePairScenario
}>()

const emit = defineEmits<{
  override: [field: 'spot' | 'volatility' | 'rfRateBase' | 'rfRateQuote', value: number | null]
}>()

const hasDefaults = computed(() => {
  return props.pair.defaultSpot != null || props.pair.defaultVol != null
    || props.pair.defaultRfBase != null || props.pair.defaultRfQuote != null
})

function fmtVal(val: number | null | undefined, decimals = 4): string {
  if (val == null) return '—'
  return val.toFixed(decimals)
}

function onSliderChange(
  field: 'spot' | 'volatility' | 'rfRateBase' | 'rfRateQuote',
  event: Event,
) {
  const val = parseFloat((event.target as HTMLInputElement).value)
  emit('override', field, isNaN(val) ? null : val)
}

function onInputChange(
  field: 'spot' | 'volatility' | 'rfRateBase' | 'rfRateQuote',
  event: Event,
) {
  const raw = (event.target as HTMLInputElement).value
  const val = raw === '' ? null : parseFloat(raw)
  emit('override', field, val)
}
</script>

<template>
  <div class="pair-controls">
    <div class="pair-header">
      <h4>{{ pair.ccyPair }}</h4>
      <span v-if="pair.curveDate" class="curve-date">曲线日: {{ pair.curveDate }}</span>
    </div>

    <div v-if="!hasDefaults" class="no-data-hint">
      未获取到该货币对的默认参数，可手动输入估值参数。
    </div>

    <div class="control-grid">
      <!-- Spot -->
      <div class="control-row">
        <label class="control-label">
          即期汇率 (Spot)
          <span class="default-val">{{ fmtVal(pair.defaultSpot) }}</span>
        </label>
        <div class="control-inputs">
          <input
            type="range"
            class="slider"
            :min="pair.defaultSpot != null ? pair.defaultSpot * 0.8 : 1"
            :max="pair.defaultSpot != null ? pair.defaultSpot * 1.2 : 50"
            :step="pair.defaultSpot != null ? pair.defaultSpot * 0.001 : 0.01"
            :value="pair.currentSpot ?? pair.defaultSpot ?? 0"
            @input="onSliderChange('spot', $event)"
          />
          <input
            type="number"
            class="num-input"
            :value="pair.currentSpot != null ? pair.currentSpot : ''"
            :placeholder="fmtVal(pair.defaultSpot)"
            step="0.0001"
            @input="onInputChange('spot', $event)"
          />
        </div>
      </div>

      <!-- Volatility -->
      <div class="control-row">
        <label class="control-label">
          波动率 (Vol) %
          <span class="default-val">{{ pair.defaultVol != null ? (pair.defaultVol * 100).toFixed(2) : '—' }}</span>
        </label>
        <div class="control-inputs">
          <input
            type="range"
            class="slider"
            :min="0.1"
            :max="pair.defaultVol != null ? pair.defaultVol * 100 * 3 : 30"
            :step="0.1"
            :value="pair.currentVol ?? (pair.defaultVol != null ? pair.defaultVol * 100 : 0)"
            @input="onSliderChange('volatility', $event)"
          />
          <input
            type="number"
            class="num-input"
            :value="pair.currentVol != null ? pair.currentVol : ''"
            :placeholder="pair.defaultVol != null ? (pair.defaultVol * 100).toFixed(2) : ''"
            step="0.1"
            min="0"
            @input="onInputChange('volatility', $event)"
          />
        </div>
      </div>

      <!-- Base rate -->
      <div class="control-row">
        <label class="control-label">
          Base 利率 %
          <span class="default-val">{{ pair.defaultRfBase != null ? (pair.defaultRfBase * 100).toFixed(2) : '—' }}</span>
        </label>
        <div class="control-inputs">
          <input
            type="range"
            class="slider"
            :min="0"
            :max="pair.defaultRfBase != null ? pair.defaultRfBase * 100 * 3 : 20"
            :step="0.05"
            :value="pair.currentRfBase ?? (pair.defaultRfBase != null ? pair.defaultRfBase * 100 : 0)"
            @input="onSliderChange('rfRateBase', $event)"
          />
          <input
            type="number"
            class="num-input"
            :value="pair.currentRfBase != null ? pair.currentRfBase : ''"
            :placeholder="pair.defaultRfBase != null ? (pair.defaultRfBase * 100).toFixed(2) : ''"
            step="0.01"
            @input="onInputChange('rfRateBase', $event)"
          />
        </div>
      </div>

      <!-- Quote rate -->
      <div class="control-row">
        <label class="control-label">
          Quote 利率 %
          <span class="default-val">{{ pair.defaultRfQuote != null ? (pair.defaultRfQuote * 100).toFixed(2) : '—' }}</span>
        </label>
        <div class="control-inputs">
          <input
            type="range"
            class="slider"
            :min="0"
            :max="pair.defaultRfQuote != null ? pair.defaultRfQuote * 100 * 3 : 20"
            :step="0.05"
            :value="pair.currentRfQuote ?? (pair.defaultRfQuote != null ? pair.defaultRfQuote * 100 : 0)"
            @input="onSliderChange('rfRateQuote', $event)"
          />
          <input
            type="number"
            class="num-input"
            :value="pair.currentRfQuote != null ? pair.currentRfQuote : ''"
            :placeholder="pair.defaultRfQuote != null ? (pair.defaultRfQuote * 100).toFixed(2) : ''"
            step="0.01"
            @input="onInputChange('rfRateQuote', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pair-controls {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1rem;
  box-shadow: var(--shadow-sm);
}
.pair-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}
.pair-header h4 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
}
.curve-date {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
}
.no-data-hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-style: italic;
  margin-bottom: 0.5rem;
}
.control-grid {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.control-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.control-label {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.default-val {
  font-weight: 400;
  opacity: 0.7;
  text-transform: none;
  letter-spacing: 0;
}
.control-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.slider {
  flex: 1;
  height: 4px;
  accent-color: var(--color-primary);
  cursor: pointer;
}
.num-input {
  width: 80px;
  padding: 0.25rem 0.4rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.75rem;
  text-align: right;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.num-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}
</style>
