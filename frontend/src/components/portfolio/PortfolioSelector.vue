<script setup lang="ts">
import { computed } from 'vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import type { Portfolio } from '@/types/portfolio'

const props = defineProps<{
  portfolios: Portfolio[]
  selectedIds: number[]
  loading: boolean
}>()

const emit = defineEmits<{
  toggle: [id: number]
  'select-all': []
}>()

const allSelected = computed(() =>
  props.portfolios.length > 0 && props.selectedIds.length === props.portfolios.length
)

const someSelected = computed(() =>
  props.selectedIds.length > 0 && props.selectedIds.length < props.portfolios.length
)
</script>

<template>
  <div class="card">
    <h3>投组管理</h3>
    <div v-if="loading"><LoadingSpinner message="加载组合..." /></div>
    <div v-else-if="portfolios.length === 0" class="placeholder-text">
      暂无投资组合。导入交易数据后将自动创建。
    </div>
    <div v-else class="portfolio-list">
      <div class="select-all-row">
        <label class="checkbox-label">
          <input
            type="checkbox"
            :checked="allSelected"
            :indeterminate="someSelected"
            @change="emit('select-all')"
          />
          <span class="select-all-text">全选</span>
        </label>
        <span class="selected-count" v-if="selectedIds.length > 0">
          已选 {{ selectedIds.length }} 个组合
        </span>
      </div>
      <div class="checkbox-grid">
        <div
          v-for="p in portfolios"
          :key="p.id"
          class="checkbox-item"
          :class="{ checked: selectedIds.includes(p.id) }"
          @click="emit('toggle', p.id)"
        >
          <label class="checkbox-label" @click.stop>
            <input
              type="checkbox"
              :checked="selectedIds.includes(p.id)"
              @change="emit('toggle', p.id)"
            />
            <div class="pf-info">
              <span class="pf-name">{{ p.name }}</span>
              <span class="pf-count">{{ p.trade_count }} 笔交易</span>
            </div>
          </label>
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
.card h3 { font-size: 0.9375rem; margin-bottom: 0.85rem; }
.placeholder-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; }
.portfolio-list { display: flex; flex-direction: column; gap: 0.5rem; }

.select-all-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0.25rem;
}
.select-all-text { font-weight: 600; font-size: 0.8125rem; }
.selected-count { font-size: 0.75rem; color: var(--color-primary); font-weight: 500; }

.checkbox-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.checkbox-item {
  padding: 0.45rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}
.checkbox-item:hover {
  border-color: var(--color-primary-lighter);
  box-shadow: var(--shadow-md);
}
.checkbox-item.checked {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: var(--shadow-blue);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}
.checkbox-label input[type="checkbox"] {
  width: 15px;
  height: 15px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.pf-info { display: flex; flex-direction: column; gap: 0.1rem; }
.pf-name { font-weight: 600; }
.pf-count { font-size: 0.7rem; color: var(--color-text-secondary); }
</style>
