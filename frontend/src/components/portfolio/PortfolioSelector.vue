<script setup lang="ts">
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import type { Portfolio } from '@/types/portfolio'

defineProps<{
  portfolios: Portfolio[]
  currentPortfolio: Portfolio | null
  loading: boolean
}>()

const emit = defineEmits<{
  select: [id: number]
}>()
</script>

<template>
  <div class="card">
    <h3>投资组合</h3>
    <div v-if="loading"><LoadingSpinner message="加载组合..." /></div>
    <div v-else-if="portfolios.length === 0" class="placeholder-text">
      暂无投资组合。导入交易数据后将自动创建。
    </div>
    <div v-else class="portfolio-list">
      <div
        v-for="p in portfolios"
        :key="p.id"
        class="portfolio-item"
        :class="{ active: currentPortfolio?.id === p.id }"
        @click="emit('select', p.id)"
      >
        <div class="pf-info">
          <span class="pf-name">{{ p.name }}</span>
          <span class="pf-count">{{ p.trade_count }} 笔交易</span>
        </div>
        <svg
          v-if="currentPortfolio?.id === p.id"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M5 13l4 4L19 7" />
        </svg>
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
.card h3 { font-size: 0.9375rem; margin-bottom: 0.85rem; }
.placeholder-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; }
.portfolio-list { display: flex; flex-wrap: wrap; gap: 0.65rem; }
.portfolio-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}
.portfolio-item:hover {
  border-color: var(--color-primary-lighter);
  box-shadow: var(--shadow-md);
}
.portfolio-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: var(--shadow-blue);
}
.pf-info { display: flex; flex-direction: column; gap: 0.1rem; }
.pf-name { font-weight: 600; }
.pf-count { font-size: 0.7rem; color: var(--color-text-secondary); }
.portfolio-item.active svg { color: var(--color-primary); }
</style>
