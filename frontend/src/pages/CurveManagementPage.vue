<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useCurveStore } from '@/stores/curveStore'
import { useUiStore } from '@/stores/uiStore'
import DataTable from '@/components/shared/DataTable.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import { exportFxImpliedRates } from '@/api/curves'
import type { TableColumn } from '@/components/shared/DataTable.vue'
import type { FxImpliedRate } from '@/types/curve'

const store = useCurveStore()
const ui = useUiStore()

// ---- filter form state ----
const filterDateFrom = ref<string>('')
const filterDateTo = ref<string>('')
const filterCurrency = ref<string>('')
const filterTenor = ref<string>('')

// ---- table columns ----
const columns: TableColumn[] = [
  { key: 'curve_date', label: '日期', sortable: true, width: '110px' },
  { key: 'foreign_currency', label: '外币', sortable: true, width: '80px' },
  { key: 'tenor', label: '期限', sortable: true, width: '70px' },
  { key: 'foreign_implied_rate', label: '隐含利率(%)', sortable: true, align: 'right' },
  { key: 'cny_risk_free_rate', label: '人民币利率(%)', sortable: true, align: 'right' },
  { key: 'spot_rate', label: '即期汇率', sortable: true, align: 'right' },
  { key: 'swap_points', label: '掉期点(Pips)', sortable: true, align: 'right' },
]

// ---- actions ----
function applyFilters() {
  store.setFilters({
    date_from: filterDateFrom.value || undefined,
    date_to: filterDateTo.value || undefined,
    currency: filterCurrency.value || undefined,
    tenor: filterTenor.value || undefined,
  })
}

function resetFilters() {
  filterDateFrom.value = ''
  filterDateTo.value = ''
  filterCurrency.value = ''
  filterTenor.value = ''
  store.setFilters({ page: 1, page_size: 10 })
}

async function handleRefresh() {
  const result = await store.refresh()
  if (result.status === 'success') {
    ui.addNotification('success', `数据刷新完成：新增 ${result.records_added} 条记录`)
  } else if (result.status === 'partial') {
    ui.addNotification('warning', `部分数据刷新成功：新增 ${result.records_added} 条记录`)
  } else {
    ui.addNotification('error', result.error_message || '数据刷新失败')
  }
}

async function handleExport() {
  try {
    const blob = await exportFxImpliedRates({
      date_from: filterDateFrom.value || undefined,
      date_to: filterDateTo.value || undefined,
      currency: filterCurrency.value || undefined,
      tenor: filterTenor.value || undefined,
      sort_by: store.filters.sort_by,
      sort_order: store.filters.sort_order,
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `fx_implied_rates_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ui.addNotification('success', '曲线数据导出成功')
  } catch (e) {
    ui.addNotification('error', e instanceof Error ? e.message : '导出失败')
  }
}

function handlePageChange(page: number) {
  store.goToPage(page)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ---- pagination ----
const visiblePages = computed(() => {
  const total = store.totalPages
  const current = store.currentPage
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  if (current <= 4) {
    return [1, 2, 3, 4, 5, '...', total]
  }
  if (current >= total - 3) {
    return [1, '...', total - 4, total - 3, total - 2, total - 1, total]
  }
  return [1, '...', current - 1, current, current + 1, '...', total]
})

// ---- init ----
onMounted(() => {
  store.init()
})
</script>

<template>
  <div class="curve-page">
    <!-- Header -->
    <header class="page-header">
      <div>
        <h1>曲线管理</h1>
        <p class="page-desc">
          管理各类利率曲线数据，用于期权估值与风险分析
        </p>
      </div>
    </header>

    <!-- Info bar -->
    <section class="info-bar">
      <div class="info-items">
        <div class="info-item">
          <span class="info-label">曲线类型</span>
          <span class="info-value">
            {{ store.activeDefinition?.name ?? '外币隐含利率曲线' }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">总记录数</span>
          <span class="info-value">{{ store.coverage?.total_records?.toLocaleString() ?? '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">日期范围</span>
          <span class="info-value">
            <template v-if="store.coverage?.date_from">
              {{ store.coverage.date_from }} ~ {{ store.coverage.date_to }}
            </template>
            <template v-else>-</template>
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">最后更新</span>
          <span class="info-value">
            {{ store.coverage?.last_updated?.slice(0, 19) ?? '尚未获取数据' }}
          </span>
        </div>
      </div>
      <button
        class="btn btn-primary"
        :disabled="store.refreshing"
        @click="handleRefresh"
      >
        <span v-if="store.refreshing" class="spinner-inline" />
        {{ store.refreshing ? '刷新中...' : '刷新数据' }}
      </button>
    </section>

    <!-- Filter bar -->
    <section class="filter-bar">
      <div class="filter-row">
        <div class="filter-group">
          <label for="filter-date-from">日期从</label>
          <input
            id="filter-date-from"
            v-model="filterDateFrom"
            type="date"
            class="filter-input"
          />
        </div>
        <div class="filter-group">
          <label for="filter-date-to">日期至</label>
          <input
            id="filter-date-to"
            v-model="filterDateTo"
            type="date"
            class="filter-input"
          />
        </div>
        <div class="filter-group">
          <label for="filter-currency">货币</label>
          <select id="filter-currency" v-model="filterCurrency" class="filter-select">
            <option value="">全部</option>
            <option
              v-for="ccy in (store.coverage?.currencies ?? [])"
              :key="ccy"
              :value="ccy"
            >
              {{ ccy }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label for="filter-tenor">期限</label>
          <select id="filter-tenor" v-model="filterTenor" class="filter-select">
            <option value="">全部</option>
            <option
              v-for="t in (store.coverage?.tenors ?? [])"
              :key="t"
              :value="t"
            >
              {{ t }}
            </option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn btn-primary" @click="applyFilters">
            <span class="btn-icon">🔍</span>查询
          </button>
          <button class="btn btn-secondary" @click="resetFilters">
            <span class="btn-icon">↺</span>重置
          </button>
          <button class="btn btn-secondary" @click="handleExport">
            <span class="btn-icon">⬇</span>导出 CSV
          </button>
        </div>
      </div>
    </section>

    <!-- Content area -->
    <section class="content-area">
      <!-- Error state -->
      <div v-if="store.error" class="state-card error">
        <p>加载失败：{{ store.error }}</p>
        <button class="btn btn-secondary" @click="store.loadRates()">重试</button>
      </div>

      <!-- Empty state (no data ever loaded) -->
      <div
        v-else-if="!store.loading && store.coverage && store.coverage.total_records === 0"
        class="state-card empty"
      >
        <p>尚未获取曲线数据</p>
        <p class="hint">点击"刷新数据"从中国货币网自动获取，或手动上传 Excel 文件</p>
        <button
          class="btn btn-primary"
          :disabled="store.refreshing"
          @click="handleRefresh"
        >
          立即获取
        </button>
      </div>

      <!-- Data table -->
      <template v-else>
        <DataTable
          :columns="columns"
          :rows="(store.rates as unknown as Record<string, unknown>[])"
          :loading="store.loading"
          :sort-by="store.filters.sort_by"
          :sort-order="store.filters.sort_order"
          empty-message="暂无符合条件的曲线数据"
          @sort="store.setSort"
        >
          <!-- Custom cell rendering for numeric columns -->
          <template #cell-foreign_implied_rate="{ value }">
            {{ value != null ? (value as number).toFixed(4) : '-' }}
          </template>
          <template #cell-cny_risk_free_rate="{ value }">
            {{ value != null ? (value as number).toFixed(4) : '-' }}
          </template>
          <template #cell-spot_rate="{ value }">
            {{ value != null ? (value as number).toFixed(4) : '-' }}
          </template>
          <template #cell-swap_points="{ value }">
            {{ value != null ? (value as number).toFixed(2) : '-' }}
          </template>
          <template #cell-curve_date="{ value }">
            {{ value ?? '-' }}
          </template>
        </DataTable>

        <!-- Pagination -->
        <div v-if="store.total > 0" class="pagination">
          <span class="page-info">
            共 {{ store.total.toLocaleString() }} 条，
            第 {{ store.currentPage }} / {{ store.totalPages }} 页
          </span>
          <div class="page-controls">
            <button
              class="btn btn-sm"
              :disabled="store.currentPage <= 1"
              @click="handlePageChange(store.currentPage - 1)"
            >
              上一页
            </button>
            <template v-for="(p, idx) in visiblePages" :key="idx">
              <span v-if="p === '...'" class="page-ellipsis">…</span>
              <button
                v-else
                class="btn btn-sm"
                :class="{ active: p === store.currentPage }"
                @click="handlePageChange(p as number)"
              >
                {{ p }}
              </button>
            </template>
            <button
              class="btn btn-sm"
              :disabled="store.currentPage >= store.totalPages"
              @click="handlePageChange(store.currentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.curve-page {
  max-width: 1400px;
}

/* ---- Header ---- */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}
.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}
.page-desc {
  margin: 0.25rem 0 0;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

/* ---- Info bar ---- */
.info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  margin-bottom: 1rem;
}
.info-items {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.info-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.info-value {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
}

/* ---- Filter bar ---- */
.filter-bar {
  padding: 0.875rem 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  margin-bottom: 1rem;
}
.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
}
.filter-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.filter-group label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.filter-input,
.filter-select {
  padding: 0.4rem 0.6rem;
  font-size: 0.825rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  min-width: 130px;
}
.filter-actions {
  display: flex;
  gap: 0.6rem;
  align-items: flex-end;
  padding-bottom: 1px;
}
.filter-actions .btn {
  padding: 0.5rem 1rem;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}
.filter-actions .btn-secondary {
  background: var(--color-bg-secondary);
}
.filter-actions .btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
}
.filter-actions .btn-icon {
  font-size: 0.85rem;
  margin-right: 0.25rem;
}

/* ---- Content ---- */
.content-area {
  min-height: 300px;
}

/* ---- State cards ---- */
.state-card {
  text-align: center;
  padding: 3rem 1.5rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.state-card.error {
  border-color: var(--color-negative);
  color: var(--color-negative);
}
.state-card .hint {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

/* ---- Buttons ---- */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 1rem;
  font-size: 0.825rem;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 500;
  transition: all var(--transition-fast);
  background: var(--color-bg);
  color: var(--color-text);
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}
.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark, #1d4ed8);
}
.btn-secondary {
  border-color: var(--color-border);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--color-border);
}
.btn-ghost {
  border-color: transparent;
  background: transparent;
  color: var(--color-text-secondary);
}
.btn-ghost:hover:not(:disabled) {
  color: var(--color-text);
}
.btn-sm {
  padding: 0.3rem 0.6rem;
  font-size: 0.78rem;
}
.btn-sm.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

/* ---- Spinner ---- */
.spinner-inline {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---- Pagination ---- */
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;
  padding: 0.5rem 0;
  flex-wrap: wrap;
}
.page-info {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}
.page-controls {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  max-width: 100%;
  padding-bottom: 2px;
}
.page-ellipsis {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  user-select: none;
}
@media (max-width: 640px) {
  .pagination {
    flex-direction: column;
    align-items: flex-start;
  }
  .page-controls {
    width: 100%;
  }
}
</style>
