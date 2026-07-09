<script setup lang="ts">
import { fmt as _fmt, profitColor, toWan } from '@/utils/format'

const props = defineProps<{
  totalOptionPnlCny: number
  totalSpotPnlCny: number
  totalSwapPnlCny: number
  totalPnlCny: number
}>()

const fmt = (v: number | null | undefined, d = 2): string => _fmt(v, d)
</script>

<template>
  <div class="greeks-summary">
    <div class="greek-card greek-option-pnl">
      <span class="greek-label">期权总损益 (CNY, 万)</span>
      <span class="greek-value" :class="profitColor(props.totalOptionPnlCny)">
        {{ fmt(toWan(props.totalOptionPnlCny)) }}
      </span>
    </div>
    <div class="greek-card greek-spot-pnl">
      <span class="greek-label">即期总损益 (CNY, 万)</span>
      <span class="greek-value" :class="profitColor(props.totalSpotPnlCny)">
        {{ fmt(toWan(props.totalSpotPnlCny)) }}
      </span>
    </div>
    <div class="greek-card greek-swap-pnl">
      <span class="greek-label">掉期总损益 (CNY, 万)</span>
      <span class="greek-value" :class="profitColor(props.totalSwapPnlCny)">
        {{ fmt(toWan(props.totalSwapPnlCny)) }}
      </span>
    </div>
    <div class="greek-card greek-total-pnl">
      <span class="greek-label">总损益 (CNY, 万) = 期权 + 即期 + 掉期</span>
      <span class="greek-value" :class="profitColor(props.totalPnlCny)">
        {{ fmt(toWan(props.totalPnlCny)) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.greeks-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.25rem;
}
.greek-card {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
}
.greek-label {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
}
.greek-value {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.greek-total-pnl {
  border-color: var(--color-primary);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), transparent);
}
.greek-total-pnl .greek-value {
  font-size: 1.3rem;
}
.profit-positive { color: #059669; }
.profit-negative { color: #ef4444; }
</style>
