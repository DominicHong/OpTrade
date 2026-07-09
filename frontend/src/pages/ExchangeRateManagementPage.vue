<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useExchangeRateStore } from '@/stores/exchangeRateStore'
import { useUiStore } from '@/stores/uiStore'
import DataTable from '@/components/shared/DataTable.vue'
import { exportExchangeRates, uploadExchangeRatesCsv, createManualRate } from '@/api/exchangeRates'
import { formatBeijingTime } from '@/utils/format'
import { SUPPORTED_CCY_PAIRS } from '@/types/exchangeRate'
import type { TableColumn } from '@/components/shared/DataTable.vue'
import type { ExchangeRateManualCreate } from '@/types/exchangeRate'

const store = useExchangeRateStore()
const ui = useUiStore()

// ---- upload state ----
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// ---- import-from-curve state ----
const importDate = ref<string>(new Date().toISOString().slice(0, 10))

// ---- manual entry state ----
const showManualForm = ref(false)
const manualForm = ref<ExchangeRateManualCreate>({
  rate_date: new Date().toISOString().slice(0, 10),
  ccy_pair: 'USD/CNY',
  rate: 0,
  source: 'manual',
  source_ref: null,
})
const submittingManual = ref(false)

// ---- filter form state ----
const filterDateFrom = ref<string>('')
const filterDateTo = ref<string>('')
const filterCcyPair = ref<string>('')
const filterSource = ref<string>('')

// ---- table columns ----
const columns: TableColumn[] = [
  { key: 'rate_date', label: '日期', sortable: true, width: '110px' },
  { key: 'ccy_pair', label: '货币对', sortable: true, width: '100px' },
  { key: 'rate', label: '汇率', sortable: true, align: 'right' },
  { key: 'source', label: '来源', sortable: true, width: '140px' },
  { key: 'source_ref', label: '来源引用', sortable: false },
  { key: 'created_at', label: '创建时间', sortable: true, width: '160px' },
]

// ---- source options for filter ----
const SOURCE_OPTIONS = [
  { value: 'fx_implied_curve', label: '外币隐含利率曲线' },
  { value: 'cross_derived', label: '交叉推导' },
  { value: 'manual', label: '手动录入' },
  { value: 'upload', label: '文件上传' },
]

function sourceLabel(value: string | null): string {
  if (!value) return '—'
  return SOURCE_OPTIONS.find((s) => s.value === value)?.label ?? value
}

// ---- actions ----
function applyFilters() {
  store.setFilters({
    date_from: filterDateFrom.value || undefined,
    date_to: filterDateTo.value || undefined,
    ccy_pair: filterCcyPair.value || undefined,
    source: filterSource.value || undefined,
  })
}

function resetFilters() {
  filterDateFrom.value = ''
  filterDateTo.value = ''
  filterCcyPair.value = ''
  filterSource.value = ''
  store.setFilters({ page: 1, page_size: 50 })
}

async function handleImportFromCurve() {
  if (!importDate.value) {
    ui.addNotification('error', '请选择导入日期')
    return
  }
  ui.addNotification('info', `开始从外币隐含利率曲线导入 ${importDate.value} 的汇率...`)
  try {
    const result = await store.importForDate(importDate.value)
    ui.addNotification('success', result.message)
  } catch (e) {
    ui.notifyError(e, '导入失败')
  }
}

async function handleImportAllDates() {
  if (!confirm('将从外币隐含利率曲线的所有日期批量派生汇率，可能耗时较长，是否继续？')) {
    return
  }
  ui.addNotification('info', '开始批量导入所有日期的汇率...')
  try {
    const result = await store.importAllDates()
    ui.addNotification('success', result.message)
  } catch (e) {
    ui.notifyError(e, '批量导入失败')
  }
}

async function handleExport() {
  try {
    const blob = await exportExchangeRates({
      date_from: filterDateFrom.value || undefined,
      date_to: filterDateTo.value || undefined,
      ccy_pair: filterCcyPair.value || undefined,
      source: filterSource.value || undefined,
      sort_by: store.filters.sort_by,
      sort_order: store.filters.sort_order,
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `exchange_rates_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ui.addNotification('success', '汇率数据导出成功')
  } catch (e) {
    ui.notifyError(e, '导出失败')
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return

  if (!confirm('上传的 CSV 将覆盖同日期同货币对的现有记录，是否继续？')) {
    return
  }

  uploading.value = true
  try {
    const result = await uploadExchangeRatesCsv(file)
    ui.addNotification('success', result.message || `导入成功：新增 ${result.records_added} 条`)
    await Promise.all([store.loadRates(), store.loadCoverage()])
  } catch (e) {
    ui.notifyError(e, '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleManualSubmit() {
  if (!manualForm.value.rate_date || !manualForm.value.ccy_pair || !manualForm.value.rate) {
    ui.addNotification('error', '请填写完整：日期、货币对、汇率')
    return
  }
  submittingManual.value = true
  try {
    await createManualRate(manualForm.value)
    ui.addNotification('success', `已保存 ${manualForm.value.ccy_pair} 在 ${manualForm.value.rate_date} 的汇率`)
    showManualForm.value = false
    await Promise.all([store.loadRates(), store.loadCoverage()])
    // Reset form for next entry
    manualForm.value = {
      ...manualForm.value,
      rate: 0,
      source_ref: null,
    }
  } catch (e) {
    ui.notifyError(e, '保存失败')
  } finally {
    submittingManual.value = false
  }
}

function handlePageChange(page: number) {
  store.goToPage(page)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

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

onMounted(() => {
  store.init()
})
</script>

<template>
  <div class="er-page">
    <!-- Header -->
    <header class="page-header">
      <div>
        <h1>汇率管理</h1>
        <p class="page-desc">
          管理多币种损益折算所需的即期汇率，支持从外币隐含利率曲线派生、文件上传与手动录入
        </p>
      </div>
    </header>

    <!-- Info bar -->
    <section class="info-bar">
      <div class="info-items">
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
          <span class="info-label">货币对数</span>
          <span class="info-value">{{ store.coverage?.ccy_pairs?.length ?? 0 }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">最后更新</span>
          <span class="info-value">
            {{ store.coverage?.last_updated ? formatBeijingTime(store.coverage.last_updated) : '尚未导入' }}
          </span>
        </div>
      </div>
      <div class="info-actions">
        <input
          ref="fileInput"
          type="file"
          accept=".csv"
          class="hidden-file-input"
          @change="handleFileChange"
        />
        <button
          class="btn btn-secondary"
          :disabled="store.importing"
          @click="handleImportAllDates"
          title="从外币隐含利率曲线的所有历史日期批量派生汇率"
        >
          批量导入全部日期
        </button>
        <button
          class="btn btn-secondary"
          :disabled="store.importing"
          @click="showManualForm = !showManualForm"
        >
          {{ showManualForm ? '收起手动录入' : '手动录入' }}
        </button>
        <button
          class="btn btn-upload"
          :disabled="uploading || store.importing"
          @click="triggerUpload"
        >
          <span v-if="uploading" class="spinner-inline" />
          <span v-else class="btn-icon">⬆</span>
          {{ uploading ? '导入中...' : '上传 CSV' }}
        </button>
      </div>
    </section>

    <!-- Import-from-curve bar -->
    <section class="import-bar">
      <div class="import-group">
        <label for="import-date">从外币隐含利率曲线导入</label>
        <input
          id="import-date"
          v-model="importDate"
          type="date"
          class="filter-input"
        />
        <button
          class="btn btn-primary"
          :disabled="store.importing"
          @click="handleImportFromCurve"
        >
          <span v-if="store.importing" class="spinner-inline" />
          {{ store.importing ? '导入中...' : '导入当日汇率' }}
        </button>
      </div>
      <p class="import-hint">
        将派生 5 个 CNY 报价对（USD/EUR/HKD/GBP/JPY/CNY）+ 4 个交叉推导对（USD/HKD, USD/JPY, EUR/USD, GBP/USD）
      </p>
    </section>

    <!-- Manual entry form -->
    <section v-if="showManualForm" class="manual-form">
      <h3>手动录入汇率</h3>
      <div class="manual-row">
        <div class="filter-group">
          <label>日期</label>
          <input v-model="manualForm.rate_date" type="date" class="filter-input" />
        </div>
        <div class="filter-group">
          <label>货币对</label>
          <select v-model="manualForm.ccy_pair" class="filter-select">
            <option v-for="p in SUPPORTED_CCY_PAIRS" :key="p" :value="p">
              {{ p }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label>汇率</label>
          <input v-model.number="manualForm.rate" type="number" step="0.0001" class="filter-input" />
        </div>
        <div class="filter-group">
          <label>来源引用（可选）</label>
          <input v-model="manualForm.source_ref" type="text" class="filter-input" placeholder="如：彭博终端" />
        </div>
        <div class="filter-actions">
          <button class="btn btn-primary" :disabled="submittingManual" @click="handleManualSubmit">
            {{ submittingManual ? '保存中...' : '保存' }}
          </button>
          <button class="btn btn-secondary" @click="showManualForm = false">取消</button>
        </div>
      </div>
    </section>

    <!-- Filter bar -->
    <section class="filter-bar">
      <div class="filter-row">
        <div class="filter-group">
          <label for="filter-date-from">日期从</label>
          <input id="filter-date-from" v-model="filterDateFrom" type="date" class="filter-input" />
        </div>
        <div class="filter-group">
          <label for="filter-date-to">日期至</label>
          <input id="filter-date-to" v-model="filterDateTo" type="date" class="filter-input" />
        </div>
        <div class="filter-group">
          <label for="filter-pair">货币对</label>
          <select id="filter-pair" v-model="filterCcyPair" class="filter-select">
            <option value="">全部</option>
            <option v-for="p in (store.coverage?.ccy_pairs ?? SUPPORTED_CCY_PAIRS)" :key="p" :value="p">
              {{ p }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label for="filter-source">来源</label>
          <select id="filter-source" v-model="filterSource" class="filter-select">
            <option value="">全部</option>
            <option v-for="s in SOURCE_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
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
      <div v-if="store.error" class="state-card error">
        <p>加载失败：{{ store.error }}</p>
        <button class="btn btn-secondary" @click="store.loadRates()">重试</button>
      </div>

      <div
        v-else-if="!store.loading && store.coverage && store.coverage.total_records === 0"
        class="state-card empty"
      >
        <p>尚未导入任何汇率数据</p>
        <p class="hint">选择日期后点击「导入当日汇率」从外币隐含利率曲线派生，或点击「上传 CSV」「手动录入」</p>
      </div>

      <template v-else>
        <DataTable
          :columns="columns"
          :rows="(store.rates as unknown as Record<string, unknown>[])"
          :loading="store.loading"
          :sort-by="store.filters.sort_by"
          :sort-order="store.filters.sort_order"
          empty-message="暂无符合条件的汇率数据"
          @sort="store.setSort"
        >
          <template #cell-rate="{ value }">
            {{ value != null ? (value as number).toFixed(6) : '-' }}
          </template>
          <template #cell-source="{ value }">
            <span class="source-badge" :class="'src-' + (value || 'unknown')">
              {{ sourceLabel(value as string) }}
            </span>
          </template>
          <template #cell-source_ref="{ value }">
            {{ value || '—' }}
          </template>
          <template #cell-rate_date="{ value }">
            {{ value ?? '-' }}
          </template>
          <template #cell-created_at="{ value }">
            {{ value ? formatBeijingTime(value as string) : '-' }}
          </template>
        </DataTable>

        <div v-if="store.total > 0" class="pagination">
          <span class="page-info">
            共 {{ store.total.toLocaleString() }} 条，第 {{ store.currentPage }} / {{ store.totalPages }} 页
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
.er-page {
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
  flex-wrap: wrap;
  gap: 1rem;
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
.info-actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
}
.hidden-file-input {
  display: none;
}

/* ---- Import bar ---- */
.import-bar {
  padding: 0.875rem 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  margin-bottom: 1rem;
}
.import-group {
  display: flex;
  align-items: flex-end;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.import-group label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.import-hint {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

/* ---- Manual form ---- */
.manual-form {
  padding: 1rem 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius);
  margin-bottom: 1rem;
}
.manual-form h3 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--color-primary);
}
.manual-row {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
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

/* ---- Source badge ---- */
.source-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}
.src-fx_implied_curve {
  background: #dbeafe;
  color: #1e40af;
}
.src-cross_derived {
  background: #fef3c7;
  color: #92400e;
}
.src-manual {
  background: #fce7f3;
  color: #9d174d;
}
.src-upload {
  background: #d1fae5;
  color: #065f46;
}
.src-unknown {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
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
.btn-upload {
  background: #f97316;
  border-color: #f97316;
  color: #fff;
}
.btn-upload:hover:not(:disabled) {
  background: #ea580c;
  border-color: #ea580c;
}
.btn-secondary {
  border-color: var(--color-border);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--color-border);
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
