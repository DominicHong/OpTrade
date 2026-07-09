<script setup lang="ts">
import { computed } from 'vue'
import { fmt as _fmt, profitColor, toWan } from '@/utils/format'

const props = defineProps<{
  exposures: Record<string, number>
}>()

const CURRENCY_ORDER = ['CNY', 'USD', 'HKD', 'EUR', 'JPY', 'GBP'] as const

const items = computed(() =>
  CURRENCY_ORDER.map((ccy) => ({
    ccy,
    exposure: props.exposures[ccy] ?? 0,
  })),
)

const fmt = (v: number | null | undefined, d = 2): string => _fmt(v, d)
</script>

<template>
  <div class="greeks-summary">
    <div v-for="item in items" :key="item.ccy" class="greek-card">
      <span class="greek-label">{{ item.ccy }} 敞口 (万)</span>
      <span class="greek-value" :class="profitColor(item.exposure)">
        {{ fmt(toWan(item.exposure)) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.greeks-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.25rem;
}
.greek-card {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.65rem 0.85rem;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
}
.greek-label {
  font-size: 0.675rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
}
.greek-value {
  font-size: 1.05rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.profit-positive { color: #059669; }
.profit-negative { color: #ef4444; }
</style>
