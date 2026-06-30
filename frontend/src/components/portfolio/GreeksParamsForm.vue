<script setup lang="ts">
import { ref, watch } from 'vue'
import type { EditableOptionTradeParams } from '@/composables/useGreeksCalculation'
import type { CurveDefinition } from '@/types/curve'

const props = defineProps<{
  valuationDate: string
  curveType: string | null
  tradeParams: EditableOptionTradeParams[]
  curveDefinitions: CurveDefinition[]
  loading: boolean
  resolving: boolean
}>()

const emit = defineEmits<{
  'update:valuationDate': [value: string]
  'update:curveType': [value: string | null]
  resolveParams: []
  updateTradeParam: [tradeId: number, field: 'rfRateBase' | 'rfRateQuote' | 'spot' | 'volatility', value: number | null]
  submit: []
}>()

// Default to the first available curve when definitions load
watch(() => props.curveDefinitions, (defs) => {
  if (!props.curveType && defs.length > 0) {
    emit('update:curveType', defs[0].curve_type)
  }
}, { immediate: true })

// Local editing state to avoid formatting/interruption during typing
const editingValues = ref<Record<string, string>>({})

function syncEditingValues() {
  props.tradeParams.forEach((tp) => {
    editingValues.value[`${tp.tradeId}-rfRateBase`] = tp.rfRateBase != null ? tp.rfRateBase.toFixed(4) : ''
    editingValues.value[`${tp.tradeId}-rfRateQuote`] = tp.rfRateQuote != null ? tp.rfRateQuote.toFixed(4) : ''
    editingValues.value[`${tp.tradeId}-volatility`] = tp.volatility != null ? tp.volatility.toFixed(4) : ''
    editingValues.value[`${tp.tradeId}-spot`] = tp.spot != null ? tp.spot.toFixed(4) : ''
  })
}

watch(() => props.tradeParams, syncEditingValues, { immediate: true, deep: true })

function onTradeFieldInput(
  tradeId: number,
  field: 'rfRateBase' | 'rfRateQuote' | 'spot' | 'volatility',
  event: Event,
) {
  const input = event.target as HTMLInputElement
  editingValues.value[`${tradeId}-${field}`] = input.value
}

function onTradeFieldBlur(
  tradeId: number,
  field: 'rfRateBase' | 'rfRateQuote' | 'spot' | 'volatility',
) {
  const raw = editingValues.value[`${tradeId}-${field}`]?.trim() ?? ''
  const value = raw === '' ? null : parseFloat(raw)
  emit('updateTradeParam', tradeId, field, isNaN(value as number) ? null : value)
}

function displayValue(val: number | null | undefined, decimals = 4): string {
  if (val == null) return '—'
  return val.toFixed(decimals)
}
</script>

<template>
  <div class="card">
    <h3>计算参数</h3>

    <!-- Common parameters -->
    <div class="common-params">
      <div class="param-field">
        <label for="valuation-date">估值日期</label>
        <input
          id="valuation-date"
          type="date"
          :value="valuationDate"
          @input="emit('update:valuationDate', ($event.target as HTMLInputElement).value)"
        />
      </div>
      <div class="param-field">
        <label for="curve-type">参考曲线</label>
        <select
          id="curve-type"
          :value="curveType"
          @change="emit('update:curveType', ($event.target as HTMLSelectElement).value || null)"
        >
          <option
            v-for="def in curveDefinitions"
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
          class="btn-resolve"
          :disabled="!curveType || resolving"
          @click="emit('resolveParams')"
        >
          {{ resolving ? '解析中...' : '解析参数' }}
        </button>
      </div>
    </div>

    <!-- Curve info banner -->
    <div v-if="curveType && tradeParams.length > 0" class="curve-banner">
      <span v-if="tradeParams.some(t => t.curveResolved)">
        📊 曲线参数已解析。蓝色背景单元格为曲线推导值，可直接修改覆盖。
      </span>
      <span v-else>⚠️ 未找到曲线数据，参数将使用交易自带值或默认值。</span>
    </div>

    <!-- Per-trade parameter table -->
    <div v-if="tradeParams.length > 0" class="trade-table-wrap">
      <table class="trade-params-table">
        <thead>
          <tr>
            <th>交易ID</th>
            <th>货币对</th>
            <th>类型</th>
            <th>方向</th>
            <th>行权价</th>
            <th>到期日</th>
            <th>剩余期限(年)</th>
            <th>Base利率%</th>
            <th>Quote利率%</th>
            <th>波动率%</th>
            <th>即期汇率</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="tp in tradeParams"
            :key="tp.tradeId"
            :class="{ 'row-curve-resolved': tp.curveResolved }"
          >
            <td class="cell-info">{{ tp.tradeIdStr ?? tp.tradeId }}</td>
            <td class="cell-info">{{ tp.ccyPair ?? '—' }}</td>
            <td class="cell-info">
              <span v-if="tp.optionType" :class="tp.optionType === 'CALL' ? 'badge-call' : 'badge-put'">
                {{ tp.optionType }}
              </span>
              <span v-else>—</span>
            </td>
            <td class="cell-info">{{ tp.direction ?? '—' }}</td>
            <td class="cell-info">{{ tp.strike != null ? tp.strike.toFixed(4) : '—' }}</td>
            <td class="cell-info">{{ tp.expiryDate ?? '—' }}</td>
            <td class="cell-info">{{ displayValue(tp.remainingMaturityYears) }}</td>
            <td class="cell-editable" :class="{ 'cell-from-curve': tp.curveResolved }">
              <input
                type="text"
                inputmode="decimal"
                :value="editingValues[`${tp.tradeId}-rfRateBase`]"
                :placeholder="tp.curveResolved ? '曲线推导' : '默认3.0'"
                @input="onTradeFieldInput(tp.tradeId, 'rfRateBase', $event)"
                @blur="onTradeFieldBlur(tp.tradeId, 'rfRateBase')"
              />
            </td>
            <td class="cell-editable" :class="{ 'cell-from-curve': tp.curveResolved }">
              <input
                type="text"
                inputmode="decimal"
                :value="editingValues[`${tp.tradeId}-rfRateQuote`]"
                :placeholder="tp.curveResolved ? '曲线推导' : '默认3.0'"
                @input="onTradeFieldInput(tp.tradeId, 'rfRateQuote', $event)"
                @blur="onTradeFieldBlur(tp.tradeId, 'rfRateQuote')"
              />
            </td>
            <td class="cell-editable" :class="{ 'cell-from-curve': tp.curveResolved }">
              <input
                type="text"
                inputmode="decimal"
                :value="editingValues[`${tp.tradeId}-volatility`]"
                :placeholder="tp.curveResolved ? '曲线推导' : '默认5.0'"
                @input="onTradeFieldInput(tp.tradeId, 'volatility', $event)"
                @blur="onTradeFieldBlur(tp.tradeId, 'volatility')"
              />
            </td>
            <td class="cell-editable" :class="{ 'cell-from-curve': tp.curveResolved }">
              <input
                type="text"
                inputmode="decimal"
                :value="editingValues[`${tp.tradeId}-spot`]"
                :placeholder="tp.curveResolved ? '曲线推导' : '默认6.8'"
                @input="onTradeFieldInput(tp.tradeId, 'spot', $event)"
                @blur="onTradeFieldBlur(tp.tradeId, 'spot')"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty state: no params resolved yet -->
    <div v-else-if="curveType" class="empty-hint">
      选择估值日期和参考曲线后，点击「解析参数」从曲线推导各交易的估值参数。
    </div>

    <button
      class="btn-calc"
      :disabled="loading"
      @click="emit('submit')"
    >
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
.card h3 {
  font-size: 0.9375rem;
  margin-bottom: 0.85rem;
}

/* ---- Common params row ---- */
.common-params {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 1rem;
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
.param-action {
  min-width: auto;
}

/* ---- Buttons ---- */
.btn-resolve {
  padding: 0.45rem 0.9rem;
  background: var(--color-bg);
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}
.btn-resolve:hover:not(:disabled) {
  background: var(--color-primary);
  color: #fff;
}
.btn-resolve:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
  margin-top: 0.75rem;
}
.btn-calc:hover { filter: brightness(1.1); }
.btn-calc:disabled { opacity: 0.6; cursor: not-allowed; }

/* ---- Banner ---- */
.curve-banner {
  font-size: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-primary-bg);
  border-radius: var(--radius);
  margin-bottom: 0.75rem;
  color: var(--color-primary);
}

/* ---- Table ---- */
.trade-table-wrap {
  overflow-x: auto;
  margin-bottom: 0.75rem;
}
.trade-params-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.trade-params-table th,
.trade-params-table td {
  padding: 0.4rem 0.5rem;
  text-align: center;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.trade-params-table th {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  background: var(--color-bg);
  position: sticky;
  top: 0;
}
.cell-info {
  color: var(--color-text);
}
.cell-editable input {
  width: 80px;
  padding: 0.3rem 0.4rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.75rem;
  text-align: center;
  background: var(--color-bg);
  color: var(--color-text);
  transition: all var(--transition-fast);
}
.cell-editable input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary-bg);
}
/* Curve-resolved cells: light blue background */
.cell-from-curve input {
  background: #e8f0fe;
  border-color: #93c5fd;
}
.cell-from-curve input:focus {
  background: var(--color-bg);
}

/* ---- Empty hint ---- */
.empty-hint {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-style: italic;
  padding: 1rem 0;
}

/* ---- Badges ---- */
.badge-call {
  background: var(--color-positive-bg);
  color: var(--color-positive);
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.badge-put {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
</style>
