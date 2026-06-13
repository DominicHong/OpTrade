<script setup lang="ts" generic="T extends Record<string, unknown>">
import { computed } from 'vue'

export interface TableColumn {
  key: string
  label: string
  sortable?: boolean
  width?: string
  align?: 'left' | 'right' | 'center'
}

const props = withDefaults(defineProps<{
  columns: TableColumn[]
  rows: T[]
  loading?: boolean
  sortBy?: string
  sortOrder?: string
  emptyMessage?: string
}>(), {
  loading: false,
  sortBy: '',
  sortOrder: 'asc',
  emptyMessage: '暂无数据',
})

const emit = defineEmits<{
  'sort': [column: string]
  'row-click': [row: T]
}>()

function onHeaderClick(col: TableColumn) {
  if (col.sortable) {
    emit('sort', col.key)
  }
}
</script>

<template>
  <div class="data-table-wrapper">
    <table class="data-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :class="{
              sortable: col.sortable,
              active: sortBy === col.key,
              [col.align || 'left']: true,
            }"
            :style="{ width: col.width }"
            @click="onHeaderClick(col)"
          >
            {{ col.label }}
            <span v-if="sortBy === col.key" class="sort-arrow">
              {{ sortOrder === 'asc' ? '▲' : '▼' }}
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td :colspan="columns.length" class="empty-cell">
            <div class="loading-cell">
              <div class="loading-dots">
                <span></span><span></span><span></span>
              </div>
              加载中...
            </div>
          </td>
        </tr>
        <tr v-else-if="rows.length === 0">
          <td :colspan="columns.length" class="empty-cell">{{ emptyMessage }}</td>
        </tr>
        <tr
          v-for="(row, idx) in rows"
          :key="idx"
          @click="emit('row-click', row)"
          class="data-row"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            :class="col.align || 'left'"
          >
            <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.data-table-wrapper {
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.data-table th, .data-table td {
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--color-border-light);
  white-space: nowrap;
}
.data-table th {
  background: var(--color-bg-secondary);
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
  text-align: left;
  position: sticky;
  top: 0;
}
.data-table th.sortable { cursor: pointer; user-select: none; }
.data-table th.sortable:hover { background: var(--color-bg-hover); color: var(--color-text); }
.data-table th.active { color: var(--color-primary); background: var(--color-primary-bg); }
.data-table th.right, .data-table td.right { text-align: right; }
.data-table th.center, .data-table td.center { text-align: center; }
.data-row {
  cursor: pointer;
  transition: background var(--transition-fast);
}
.data-row:hover { background: var(--color-primary-bg); }
.data-row:last-child td { border-bottom: none; }
.sort-arrow { font-size: 0.625rem; margin-left: 2px; }
.empty-cell { text-align: center; padding: 2.5rem; color: var(--color-text-secondary); }
.loading-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
.loading-dots {
  display: flex;
  gap: 4px;
}
.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse 1.2s ease-in-out infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
</style>
