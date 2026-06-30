<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useOptionTradeStore } from '@/stores/optionTradeStore'
import { useSpotTradeStore } from '@/stores/spotTradeStore'
import { useUiStore } from '@/stores/uiStore'
import { uploadFile, getColumnMapping } from '@/api/imports'
import { uploadSpotFile, getSpotColumnMapping as getSpotColumnMappingApi } from '@/api/spotTrades'
import DataTable from '@/components/shared/DataTable.vue'
import SearchInput from '@/components/shared/SearchInput.vue'
import NumberDisplay from '@/components/shared/NumberDisplay.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import PortfolioAutocomplete from '@/components/trade/PortfolioAutocomplete.vue'
import type { TableColumn } from '@/components/shared/DataTable.vue'
import type { OptionTrade, OptionTradeCreate, OptionTradeUpdate } from '@/types/optionTrade'
import type { SpotTrade, SpotTradeCreate, SpotTradeUpdate } from '@/types/spotTrade'
import type { ImportConfirmResponse } from '@/types/api'
import { formatDate, toWan } from '@/utils/format'
import { useModalGuard } from '@/composables/useModalGuard'

const router = useRouter()
const store = useOptionTradeStore()
const spotStore = useSpotTradeStore()
const ui = useUiStore()
const search = ref('')
const spotSearch = ref('')

// --- Tab state ---
const activeTab = ref<'list' | 'import' | 'mapping'>('list')

// --- Import state ---
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const importResult = ref<ImportConfirmResponse | null>(null)
const importType = ref<'option' | 'spot'>('option')
const columnMapping = ref<Record<string, string>>({})
const spotColumnMapping = ref<Record<string, string>>({})

// --- Trade form modal ---
const showModal = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const formError = ref<string | null>(null)
const formLoading = ref(false)

// Track which premium field the user is actively editing
const premiumEditingField = ref<'rate' | 'amount' | null>(null)

// --- Spot trade form modal ---
const showSpotModal = ref(false)
const spotModalMode = ref<'create' | 'edit'>('create')
const spotFormError = ref<string | null>(null)
const spotFormLoading = ref(false)
const spotEditingId = ref<number | null>(null)
const spotFormPortfolioId = ref<number | null>(null)

const emptySpotForm: SpotTradeCreate = {
  trade_id: '',
  ccy_pair: 'USD/CNY',
  direction: '买入',
  event_type: '正常',
  deal_price: null,
  ccy1_amount: null,
  ccy2_amount: null,
  trade_date: null,
  value_date: null,
  counterparty_name: null,
  portfolio_name: null,
  delivery_status: null,
  source: null,
  venue: null,
}

const spotForm = ref<SpotTradeCreate | SpotTradeUpdate>({ ...emptySpotForm })

const emptyForm: OptionTradeCreate = {
  trade_id: '',
  ccy_pair: 'USD/CNY',
  trade_type: 'CALL',
  direction: '买入',
  strike: null,
  notional1: null,
  notional2: null,
  expiry_date: null,
  counterparty_name: null,
  portfolio_name: null,
  option_type: null,
  premium_type: null,
  premium_rate: null,
  premium_amount: null,
  premium_currency: null,
}

const form = ref<OptionTradeCreate | OptionTradeUpdate>({ ...emptyForm })
const editingTradeId = ref<number | null>(null)
const formPortfolioId = ref<number | null>(null)

/** Determine which notional to use for premium calc based on premium_type + premium_currency + ccy_pair. */
function getNotionalForCalc(): number | null {
  const type = form.value.premium_type
  const currency = form.value.premium_currency
  const ccyPair = form.value.ccy_pair
  if (!type || !currency || !ccyPair) return null

  const parts = ccyPair.split('/')
  if (parts.length !== 2) return null
  const [ccy1, ccy2] = parts
  const isCcy2 = currency === ccy2

  if (type === 'Pips') {
    // Pips + ccy2 -> notional1; Pips + ccy1 -> notional2
    return (isCcy2 ? form.value.notional1 : form.value.notional2) ?? null
  } else {
    // % + ccy2 -> notional2; % + ccy1 -> notional1
    return (isCcy2 ? form.value.notional2 : form.value.notional1) ?? null
  }
}

/** Compute premium amount from rate. */
function calcPremiumFromRate() {
  const rate = form.value.premium_rate
  const type = form.value.premium_type
  const notional = getNotionalForCalc()
  if (rate == null || notional == null || !type) return
  if (type === 'Pips') {
    form.value.premium_amount = Number((rate * notional / 10000).toFixed(2))
  } else if (type === '%') {
    form.value.premium_amount = Number((rate * notional / 100).toFixed(2))
  }
}

/** Compute premium rate from amount. */
function calcPremiumRateFromAmount() {
  const amount = form.value.premium_amount
  const type = form.value.premium_type
  const notional = getNotionalForCalc()
  if (amount == null || notional == null || !type || notional === 0) return
  if (type === 'Pips') {
    form.value.premium_rate = Number((amount * 10000 / notional).toFixed(4))
  } else if (type === '%') {
    form.value.premium_rate = Number((amount * 100 / notional).toFixed(4))
  }
}

function onPremiumRateInput() {
  premiumEditingField.value = 'rate'
  calcPremiumFromRate()
}

function onPremiumAmountInput() {
  premiumEditingField.value = 'amount'
  calcPremiumRateFromAmount()
}

// When premium_type, premium_currency, notional1 or notional2 changes, recalculate
watch(() => form.value.premium_type, () => {
  if (premiumEditingField.value === 'rate') calcPremiumFromRate()
  else if (premiumEditingField.value === 'amount') calcPremiumRateFromAmount()
})

watch(() => form.value.premium_currency, () => {
  if (premiumEditingField.value === 'rate') calcPremiumFromRate()
  else if (premiumEditingField.value === 'amount') calcPremiumRateFromAmount()
})

watch(() => form.value.notional1, () => {
  if (premiumEditingField.value === 'rate') calcPremiumFromRate()
  else if (premiumEditingField.value === 'amount') calcPremiumRateFromAmount()
})

watch(() => form.value.notional2, () => {
  if (premiumEditingField.value === 'rate') calcPremiumFromRate()
  else if (premiumEditingField.value === 'amount') calcPremiumRateFromAmount()
})

// --- Batch selection ---
const selectedIds = ref<number[]>([])
const showBatchDeleteConfirm = ref(false)
const spotSelectedIds = ref<number[]>([])
const showSpotBatchDeleteConfirm = ref(false)

function onSelectionChange(ids: number[]) {
  selectedIds.value = ids
}

function confirmBatchDelete() {
  if (selectedIds.value.length === 0) return
  showBatchDeleteConfirm.value = true
}

async function doBatchDelete() {
  try {
    const count = await store.batchDelete(selectedIds.value)
    ui.addNotification('success', `已删除 ${count} 条交易`)
    selectedIds.value = []
  } catch (e: unknown) {
    ui.addNotification('error', e instanceof Error ? e.message : '批量删除失败')
  } finally {
    showBatchDeleteConfirm.value = false
  }
}

function cancelBatchDelete() {
  showBatchDeleteConfirm.value = false
}

function onSpotSelectionChange(ids: number[]) {
  spotSelectedIds.value = ids
}

function confirmSpotBatchDelete() {
  if (spotSelectedIds.value.length === 0) return
  showSpotBatchDeleteConfirm.value = true
}

async function doSpotBatchDelete() {
  try {
    const count = await spotStore.batchDelete(spotSelectedIds.value)
    ui.addNotification('success', `已删除 ${count} 条即期流水`)
    spotSelectedIds.value = []
  } catch (e: unknown) {
    ui.addNotification('error', e instanceof Error ? e.message : '批量删除失败')
  } finally {
    showSpotBatchDeleteConfirm.value = false
  }
}

function cancelSpotBatchDelete() {
  showSpotBatchDeleteConfirm.value = false
}

const columns = computed<TableColumn[]>(() => {
  const types = new Set(store.trades.map(t => t.premium_type).filter(Boolean) as string[])
  const premiumRateLabel =
    types.size === 1 && types.has('Pips') ? '期权费率(pips)'
    : types.size === 1 && types.has('%') ? '期权费率(%)'
    : '期权费率'

  return [
    { key: 'actions', label: '编辑', width: '100px' },
    { key: 'trade_id', label: '成交编号', sortable: true, width: '140px' },
    { key: 'ccy_pair', label: '货币对', sortable: true, width: '90px' },
    { key: 'trade_type', label: '类型', sortable: true, width: '60px' },
    { key: 'direction', label: '方向', sortable: true, width: '60px' },
    { key: 'strike', label: '执行价', sortable: true, width: '90px', align: 'right' },
    { key: 'premium_rate', label: premiumRateLabel, sortable: true, width: '90px', align: 'right' },
    { key: 'notional1', label: '名义本金(万)', sortable: true, width: '120px', align: 'right' },
    { key: 'expiry_date', label: '到期日', sortable: true, width: '100px' },
    { key: 'counterparty_name', label: '对手方', width: '120px' },
    { key: 'exercise_status', label: '行权状态', width: '80px' },
    { key: 'delivery_status', label: '交割状态', width: '80px' },
  ]
})

// --- Spot trade columns ---
const spotColumns = computed<TableColumn[]>(() => [
  { key: 'actions', label: '操作', width: '100px' },
  { key: 'trade_id', label: '成交编号', sortable: true, width: '140px' },
  { key: 'ccy_pair', label: '货币对', sortable: true, width: '90px' },
  { key: 'direction', label: '方向', sortable: true, width: '60px' },
  { key: 'event_type', label: '事件类型', sortable: true, width: '110px' },
  { key: 'deal_price', label: '成交价', sortable: true, width: '90px', align: 'right' as const },
  { key: 'ccy1_amount', label: '货币1金额(万)', sortable: true, width: '120px', align: 'right' as const },
  { key: 'ccy2_amount', label: '货币2金额(万)', sortable: true, width: '120px', align: 'right' as const },
  { key: 'trade_date', label: '交易日', sortable: true, width: '100px' },
  { key: 'value_date', label: '起息日', sortable: true, width: '100px' },
  { key: 'counterparty_name', label: '对手方', width: '120px' },
  { key: 'delivery_status', label: '交割状态', width: '80px' },
])

onMounted(() => {
  store.loadTrades()
  spotStore.loadTrades()
  loadColumnMapping()
})

watch(search, (val) => {
  store.setFilters({ search: val })
  selectedIds.value = []
})

watch(spotSearch, (val) => {
  spotStore.setFilters({ search: val })
  spotSelectedIds.value = []
})

function onSort(col: string) {
  const order = store.filters.sort_by === col && store.filters.sort_order === 'asc' ? 'desc' : 'asc'
  store.setFilters({ sort_by: col, sort_order: order })
}

function onRowClick(row: Record<string, unknown>) {
  const trade = row as unknown as OptionTrade
  router.push(`/option-trades/${trade.id}`)
}

function onSpotSort(col: string) {
  const order = spotStore.filters.sort_by === col && spotStore.filters.sort_order === 'asc' ? 'desc' : 'asc'
  spotStore.setFilters({ sort_by: col, sort_order: order })
}

function onSpotRowClick(row: Record<string, unknown>) {
  // Spot trades have no detail page; click does nothing for now
}

// --- Import ---
function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) {
    importFile.value = input.files[0]
  }
}

async function handleUpload() {
  if (!importFile.value) return
  importLoading.value = true
  try {
    const result = importType.value === 'spot'
      ? await uploadSpotFile(importFile.value)
      : await uploadFile(importFile.value)
    importResult.value = result
    const msg = `导入完成: ${result.imported_rows} 行成功, ${result.skipped_rows} 跳过, ${result.error_rows} 错误`
    ui.addNotification(result.status === 'success' ? 'success' : 'warning', msg)
    if (importType.value === 'spot') {
      spotStore.loadTrades()
    } else {
      store.loadTrades()
    }
  } catch (e: unknown) {
    ui.addNotification('error', e instanceof Error ? e.message : '导入失败')
  } finally {
    importLoading.value = false
  }
}

async function loadColumnMapping() {
  try {
    const result = await getColumnMapping()
    columnMapping.value = result.mapping
  } catch { /* ignore */ }
  try {
    const result = await getSpotColumnMappingApi()
    spotColumnMapping.value = result.mapping
  } catch { /* ignore */ }
}

// --- Create / Edit ---
function openCreateModal() {
  modalMode.value = 'create'
  form.value = { ...emptyForm }
  editingTradeId.value = null
  formPortfolioId.value = null
  formError.value = null
  showModal.value = true
}

function openEditModal(trade: OptionTrade) {
  modalMode.value = 'edit'
  editingTradeId.value = trade.id
  formPortfolioId.value = trade.portfolio_id
  form.value = {
    trade_id: trade.trade_id,
    ccy_pair: trade.ccy_pair,
    trade_type: trade.trade_type,
    direction: trade.direction,
    strike: trade.strike,
    notional1: trade.notional1,
    notional2: trade.notional2,
    expiry_date: trade.expiry_date,
    counterparty_name: trade.counterparty_name,
    portfolio_name: trade.portfolio_name,
    option_type: trade.option_type,
    source_trade_id: trade.source_trade_id,
    spot_rate: trade.spot_rate,
    volatility: trade.volatility != null ? trade.volatility * 100 : null,
    premium_type: trade.premium_type,
    premium_rate: trade.premium_rate,
    premium_amount: trade.premium_amount,
    premium_currency: trade.premium_currency,
    exercise_status: trade.exercise_status,
    delivery_status: trade.delivery_status,
    comments: trade.comments,
  }
  formError.value = null
  showModal.value = true
}

async function submitForm() {
  formLoading.value = true
  formError.value = null
  const payload = { ...form.value, portfolio_id: formPortfolioId.value }
  if (payload.volatility != null) {
    payload.volatility = payload.volatility / 100
  }
  try {
    if (modalMode.value === 'create') {
      await store.addTrade(payload as OptionTradeCreate)
      ui.addNotification('success', '交易创建成功')
    } else if (editingTradeId.value) {
      await store.saveTrade(editingTradeId.value, payload as OptionTradeUpdate)
      ui.addNotification('success', '交易更新成功')
    }
    showModal.value = false
    store.loadTrades()
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    formLoading.value = false
  }
}

// --- Spot trade CRUD ---
function openSpotCreateModal() {
  spotModalMode.value = 'create'
  spotForm.value = { ...emptySpotForm }
  spotEditingId.value = null
  spotFormPortfolioId.value = null
  spotFormError.value = null
  showSpotModal.value = true
}

function openSpotEditModal(trade: SpotTrade) {
  spotModalMode.value = 'edit'
  spotEditingId.value = trade.id
  spotFormPortfolioId.value = trade.portfolio_id
  spotForm.value = {
    trade_id: trade.trade_id,
    ccy_pair: trade.ccy_pair,
    direction: trade.direction,
    event_type: trade.event_type,
    deal_price: trade.deal_price,
    ccy1_amount: trade.ccy1_amount,
    ccy2_amount: trade.ccy2_amount,
    trade_date: trade.trade_date,
    value_date: trade.value_date,
    counterparty_name: trade.counterparty_name,
    portfolio_name: trade.portfolio_name,
    delivery_status: trade.delivery_status,
    source: trade.source,
    venue: trade.venue,
  }
  spotFormError.value = null
  showSpotModal.value = true
}

async function submitSpotForm() {
  spotFormLoading.value = true
  spotFormError.value = null
  const payload = { ...spotForm.value, portfolio_id: spotFormPortfolioId.value }
  try {
    if (spotModalMode.value === 'create') {
      await spotStore.addTrade(payload as SpotTradeCreate)
      ui.addNotification('success', '即期流水创建成功')
    } else if (spotEditingId.value) {
      await spotStore.saveTrade(spotEditingId.value, payload as SpotTradeUpdate)
      ui.addNotification('success', '即期流水更新成功')
    }
    showSpotModal.value = false
    spotStore.loadTrades()
  } catch (e: unknown) {
    spotFormError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    spotFormLoading.value = false
  }
}

async function deleteSpotTrade(trade: SpotTrade) {
  try {
    await spotStore.removeTrade(trade.id)
    ui.addNotification('success', '即期流水已删除')
  } catch (e: unknown) {
    ui.addNotification('error', e instanceof Error ? e.message : '删除失败')
  }
}

// --- Modal overlay click guard (prevents closing on drag from inside) ---
const { onOverlayMousedown, onOverlayClick } = useModalGuard(showModal)
const { onOverlayMousedown: onSpotOverlayMousedown, onOverlayClick: onSpotOverlayClick } = useModalGuard(showSpotModal)

// Pagination
const totalPages = () => Math.ceil(store.totalCount / (store.filters.page_size || 50))
</script>

<template>
  <div class="trade-list-page">
    <div class="page-header">
      <h1>交易管理</h1>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button :class="['tab', { active: activeTab === 'list' }]" @click="activeTab = 'list'">交易列表</button>
      <button :class="['tab', { active: activeTab === 'import' }]" @click="activeTab = 'import'">数据导入</button>
      <button :class="['tab', { active: activeTab === 'mapping' }]" @click="activeTab = 'mapping'">字段映射参考</button>
    </div>

    <!-- ==================== Tab: Trade List ==================== -->
    <template v-if="activeTab === 'list'">
      <div class="toolbar">
        <SearchInput v-model="search" placeholder="搜索成交编号、货币对、对手方..." />
        <div class="filter-group">
          <select v-model="store.filters.ccy_pair" @change="store.setFilters({ ccy_pair: ($event.target as HTMLSelectElement).value || undefined })">
            <option value="">全部货币对</option>
            <option value="USD/CNY">USD/CNY</option>
            <option value="EUR/USD">EUR/USD</option>
          </select>
          <select v-model="store.filters.trade_type" @change="store.setFilters({ trade_type: ($event.target as HTMLSelectElement).value || undefined })">
            <option value="">全部类型</option>
            <option value="CALL">Call</option>
            <option value="PUT">Put</option>
          </select>
        </div>
        <div class="toolbar-spacer"></div>
        <button v-if="selectedIds.length > 0" class="btn-danger" @click="confirmBatchDelete">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          删除选中 ({{ selectedIds.length }})
        </button>
        <button class="btn-primary" @click="openCreateModal">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
          新建交易
        </button>
      </div>

      <DataTable
        :columns="columns"
        :rows="store.trades as unknown as Record<string, unknown>[]"
        :loading="store.loading"
        :sort-by="store.filters.sort_by"
        :sort-order="store.filters.sort_order"
        selectable
        :selected-ids="selectedIds"
        row-key="id"
        @sort="onSort"
        @row-click="onRowClick"
        @update:selected-ids="onSelectionChange"
      >
        <template #cell-notional1="{ row }">
          <NumberDisplay :value="toWan(row.notional1 as number)" />
        </template>
        <template #cell-strike="{ row }">
          <NumberDisplay :value="row.strike as number" :decimals="4" />
        </template>
        <template #cell-premium_rate="{ row }">
          <NumberDisplay :value="row.premium_rate as number" :decimals="2" />
        </template>
        <template #cell-expiry_date="{ row }">
          {{ formatDate(row.expiry_date as string) }}
        </template>
        <template #cell-trade_type="{ row }">
          <span :class="row.trade_type === 'CALL' ? 'badge-call' : 'badge-put'">
            {{ row.trade_type }}
          </span>
        </template>
        <template #cell-actions="{ row }">
          <div class="action-btns" @click.stop>
            <button class="action-btn action-edit" title="编辑" @click="openEditModal(row as unknown as OptionTrade)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
          </div>
        </template>
      </DataTable>

      <!-- Pagination -->
      <div class="pagination" v-if="store.totalCount > 0">
        <button class="page-btn" :disabled="store.filters.page === 1" @click="store.setPage((store.filters.page || 1) - 1)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
          上一页
        </button>
        <span class="page-info">第 <strong>{{ store.filters.page }}</strong> / {{ totalPages() }} 页 <span class="page-total">(共 {{ store.totalCount }} 条)</span></span>
        <button class="page-btn" :disabled="(store.filters.page || 1) >= totalPages()" @click="store.setPage((store.filters.page || 1) + 1)">
          下一页
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>

      <!-- Spot trades section -->
      <div class="section-divider">
        <h2 class="section-title">即期流水</h2>
      </div>

      <div class="toolbar">
        <SearchInput v-model="spotSearch" placeholder="搜索成交编号、货币对、对手方..." />
        <div class="filter-group">
          <select v-model="spotStore.filters.ccy_pair" @change="spotStore.setFilters({ ccy_pair: ($event.target as HTMLSelectElement).value || undefined })">
            <option value="">全部货币对</option>
            <option value="USD/CNY">USD/CNY</option>
            <option value="EUR/USD">EUR/USD</option>
            <option value="EUR/CNY">EUR/CNY</option>
            <option value="GBP/USD">GBP/USD</option>
            <option value="USD/JPY">USD/JPY</option>
          </select>
          <select v-model="spotStore.filters.event_type" @change="spotStore.setFilters({ event_type: ($event.target as HTMLSelectElement).value || undefined })">
            <option value="">全部事件类型</option>
            <option value="正常">正常</option>
            <option value="期权行权衍生">期权行权衍生</option>
          </select>
        </div>
        <div class="toolbar-spacer"></div>
        <button v-if="spotSelectedIds.length > 0" class="btn-danger" @click="confirmSpotBatchDelete">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          删除选中 ({{ spotSelectedIds.length }})
        </button>
        <button class="btn-primary" @click="openSpotCreateModal">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
          新建即期
        </button>
      </div>

      <DataTable
        :columns="spotColumns"
        :rows="spotStore.trades as unknown as Record<string, unknown>[]"
        :loading="spotStore.loading"
        :sort-by="spotStore.filters.sort_by"
        :sort-order="spotStore.filters.sort_order"
        selectable
        :selected-ids="spotSelectedIds"
        row-key="id"
        @sort="onSpotSort"
        @row-click="onSpotRowClick"
        @update:selected-ids="onSpotSelectionChange"
      >
        <template #cell-deal_price="{ row }">
          <NumberDisplay :value="row.deal_price as number" :decimals="4" />
        </template>
        <template #cell-ccy1_amount="{ row }">
          <NumberDisplay :value="toWan(row.ccy1_amount as number)" />
        </template>
        <template #cell-ccy2_amount="{ row }">
          <NumberDisplay :value="toWan(row.ccy2_amount as number)" />
        </template>
        <template #cell-trade_date="{ row }">
          {{ formatDate(row.trade_date as string) }}
        </template>
        <template #cell-value_date="{ row }">
          {{ formatDate(row.value_date as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="action-btns" @click.stop>
            <button class="action-btn action-edit" title="编辑" @click="openSpotEditModal(row as unknown as SpotTrade)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button class="action-btn action-delete" title="删除" @click="deleteSpotTrade(row as unknown as SpotTrade)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </template>
      </DataTable>

      <!-- Spot pagination -->
      <div class="pagination" v-if="spotStore.totalCount > 0">
        <button class="page-btn" :disabled="spotStore.filters.page === 1" @click="spotStore.setPage((spotStore.filters.page || 1) - 1)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
          上一页
        </button>
        <span class="page-info">第 <strong>{{ spotStore.filters.page }}</strong> / {{ Math.ceil(spotStore.totalCount / (spotStore.filters.page_size || 50)) }} 页 <span class="page-total">(共 {{ spotStore.totalCount }} 条)</span></span>
        <button class="page-btn" :disabled="(spotStore.filters.page || 1) >= Math.ceil(spotStore.totalCount / (spotStore.filters.page_size || 50))" @click="spotStore.setPage((spotStore.filters.page || 1) + 1)">
          下一页
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    </template>

    <!-- ==================== Tab: Import ==================== -->
    <template v-if="activeTab === 'import'">
      <div class="import-type-selector">
        <label class="radio-label">
          <input type="radio" v-model="importType" value="option" />
          <span>期权 from ComStar</span>
        </label>
        <label class="radio-label">
          <input type="radio" v-model="importType" value="spot" />
          <span>即期 from ComStar</span>
        </label>
      </div>
      <div class="card upload-area">
        <h3>选择文件</h3>
        <p class="card-subtitle">{{ importType === 'spot' ? '导入 COMSTAR 外汇即期 Excel 交易流水文件' : '导入 COMSTAR 外汇期权 Excel/CSV 交易流水文件' }}</p>
        <div class="file-input-row">
          <div class="file-input-wrapper">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
            <span class="file-text">{{ importFile ? importFile.name : '点击选择文件...' }}</span>
            <input type="file" accept=".csv,.xlsx,.xls" @change="onFileChange" class="file-hidden" />
          </div>
          <button :disabled="!importFile || importLoading" @click="handleUpload" class="btn-primary">
            {{ importLoading ? '上传中...' : '上传并解析' }}
          </button>
        </div>
        <p v-if="importFile" class="file-info">{{ importFile.name }} ({{ (importFile.size / 1024).toFixed(1) }} KB)</p>
      </div>

      <div v-if="importLoading"><LoadingSpinner message="正在解析文件..." /></div>

      <div v-if="importResult" class="card">
        <h3>导入结果</h3>
        <div class="preview-stats">
          <div class="preview-stat">
            <span class="preview-stat-value">{{ importResult.total_rows }}</span>
            <span class="preview-stat-label">总行数</span>
          </div>
          <div class="preview-stat preview-stat--success">
            <span class="preview-stat-value">{{ importResult.imported_rows }}</span>
            <span class="preview-stat-label">成功导入</span>
          </div>
          <div class="preview-stat preview-stat--warning">
            <span class="preview-stat-value">{{ importResult.skipped_rows }}</span>
            <span class="preview-stat-label">跳过</span>
          </div>
          <div class="preview-stat preview-stat--error">
            <span class="preview-stat-value">{{ importResult.error_rows }}</span>
            <span class="preview-stat-label">错误</span>
          </div>
        </div>
        <div v-if="importResult.errors.length" class="error-list">
          <h4>错误详情 (前50条):</h4>
          <div v-for="(err, i) in importResult.errors" :key="i" class="error-item">
            <span class="err-row">行 {{ (err as Record<string, unknown>).row_number }}</span>
            <span class="err-field">{{ (err as Record<string, unknown>).field }}</span>
            <span class="err-msg">{{ (err as Record<string, unknown>).message }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- ==================== Tab: Column Mapping ==================== -->
    <template v-if="activeTab === 'mapping'">
      <div class="card" v-if="Object.keys(columnMapping).length">
        <h3>期权字段映射参考</h3>
        <p class="card-subtitle">期权 CSV 表头 → 数据库字段</p>
        <div class="mapping-grid">
          <div v-for="(field, header) in columnMapping" :key="header" class="mapping-item">
            <span class="csv-header">{{ header }}</span>
            <span class="arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </span>
            <span class="db-field">{{ field }}</span>
          </div>
        </div>
      </div>
      <div class="card" v-if="Object.keys(spotColumnMapping).length">
        <h3>即期字段映射参考</h3>
        <p class="card-subtitle">即期 Excel 表头 → 数据库字段</p>
        <div class="mapping-grid">
          <div v-for="(field, header) in spotColumnMapping" :key="header" class="mapping-item">
            <span class="csv-header">{{ header }}</span>
            <span class="arrow">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </span>
            <span class="db-field">{{ field }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- ==================== Trade Form Modal ==================== -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @mousedown="onOverlayMousedown" @click="onOverlayClick">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ modalMode === 'create' ? '新建交易' : '编辑交易' }}</h3>
            <button class="modal-close" @click="showModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="formError" class="form-error">{{ formError }}</div>
            <div class="form-grid">
              <div class="form-field">
                <label>成交编号 <span class="required">*</span></label>
                <input v-model="form.trade_id" :disabled="modalMode === 'edit'" placeholder="必填" />
              </div>
              <div class="form-field">
                <label>货币对</label>
                <select v-model="form.ccy_pair">
                  <option value="USD/CNY">USD/CNY</option>
                  <option value="EUR/USD">EUR/USD</option>
                  <option value="EUR/CNY">EUR/CNY</option>
                  <option value="GBP/USD">GBP/USD</option>
                  <option value="USD/JPY">USD/JPY</option>
                </select>
              </div>
              <div class="form-field">
                <label>交易类型</label>
                <select v-model="form.trade_type">
                  <option value="CALL">CALL</option>
                  <option value="PUT">PUT</option>
                </select>
              </div>
              <div class="form-field">
                <label>方向</label>
                <select v-model="form.direction">
                  <option value="买入">买入</option>
                  <option value="卖出">卖出</option>
                </select>
              </div>
              <div class="form-field">
                <label>执行价</label>
                <input v-model.number="form.strike" type="number" step="0.0001" placeholder="如 7.0000" />
              </div>
              <div class="form-field">
                <label>名义本金</label>
                <input v-model.number="form.notional1" type="number" step="10000" placeholder="如 1000000" />
              </div>
              <div class="form-field">
                <label>到期日</label>
                <input v-model="form.expiry_date" type="date" />
              </div>
              <div class="form-field">
                <label>对手方</label>
                <input v-model="form.counterparty_name" placeholder="对手方名称" />
              </div>
              <div class="form-field">
                <label>投组</label>
                <PortfolioAutocomplete
                  :model-value="form.portfolio_name ?? ''"
                  placeholder="搜索并选择投组..."
                  @update:model-value="(v: string | null) => form.portfolio_name = v"
                  @update:portfolio-id="(v: number | null) => formPortfolioId = v"
                />
              </div>
              <div class="form-field">
                <label>期权费类型</label>
                <select v-model="form.premium_type">
                  <option value="Pips">Pips</option>
                  <option value="%">%</option>
                </select>
              </div>
              <div class="form-field">
                <label>期权费率</label>
                <input v-model.number="form.premium_rate" type="number" step="0.0001" placeholder="如 15" @input="onPremiumRateInput" />
              </div>
              <div class="form-field">
                <label>期权费金额</label>
                <input v-model.number="form.premium_amount" type="number" step="1" placeholder="如 15000" @input="onPremiumAmountInput" />
              </div>
              <div class="form-field">
                <label>期权费货币</label>
                <select v-model="form.premium_currency">
                  <option v-if="form.ccy_pair" :value="form.ccy_pair.split('/')[0]">{{ form.ccy_pair.split('/')[0] }}</option>
                  <option v-if="form.ccy_pair" :value="form.ccy_pair.split('/')[1]">{{ form.ccy_pair.split('/')[1] }}</option>
                </select>
              </div>
              <div class="form-field">
                <label>即期汇率</label>
                <input v-model.number="form.spot_rate" type="number" step="0.0001" placeholder="如 6.8500" />
              </div>
              <div class="form-field">
                <label>波动率 (%)</label>
                <input v-model.number="form.volatility" type="number" step="0.1" placeholder="如 5" />
              </div>
              <div class="form-field">
                <label>行权状态</label>
                <select v-model="form.exercise_status">
                  <option value="未到期">未到期</option>
                  <option value="已行权">已行权</option>
                  <option value="未行权">未行权</option>
                  <option value="过期未行权">过期未行权</option>
                </select>
              </div>
              <div class="form-field">
                <label>交割状态</label>
                <select v-model="form.delivery_status">
                  <option value="未交割">未交割</option>
                  <option value="已交割">已交割</option>
                </select>
              </div>
              <div class="form-field form-field--full">
                <label>备注</label>
                <input v-model="form.comments" placeholder="备注信息" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showModal = false">取消</button>
            <button class="btn-primary" :disabled="formLoading" @click="submitForm">
              {{ formLoading ? '提交中...' : '确认' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ==================== Spot Trade Form Modal ==================== -->
    <Teleport to="body">
      <div v-if="showSpotModal" class="modal-overlay" @mousedown="onSpotOverlayMousedown" @click="onSpotOverlayClick">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ spotModalMode === 'create' ? '新建即期流水' : '编辑即期流水' }}</h3>
            <button class="modal-close" @click="showSpotModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="spotFormError" class="form-error">{{ spotFormError }}</div>
            <div class="form-grid">
              <div class="form-field">
                <label>成交编号 <span class="required">*</span></label>
                <input v-model="spotForm.trade_id" :disabled="spotModalMode === 'edit'" placeholder="必填" />
              </div>
              <div class="form-field">
                <label>货币对</label>
                <select v-model="spotForm.ccy_pair">
                  <option value="USD/CNY">USD/CNY</option>
                  <option value="EUR/USD">EUR/USD</option>
                  <option value="EUR/CNY">EUR/CNY</option>
                  <option value="GBP/USD">GBP/USD</option>
                  <option value="USD/JPY">USD/JPY</option>
                </select>
              </div>
              <div class="form-field">
                <label>方向</label>
                <select v-model="spotForm.direction">
                  <option value="买入">买入</option>
                  <option value="卖出">卖出</option>
                </select>
              </div>
              <div class="form-field">
                <label>交易事件类型</label>
                <select v-model="spotForm.event_type">
                  <option value="正常">正常</option>
                  <option value="期权行权衍生">期权行权衍生</option>
                </select>
              </div>
              <div class="form-field">
                <label>成交价</label>
                <input v-model.number="spotForm.deal_price" type="number" step="0.0001" placeholder="如 6.7813" />
              </div>
              <div class="form-field">
                <label>货币1金额</label>
                <input v-model.number="spotForm.ccy1_amount" type="number" step="1" placeholder="如 5000000" />
              </div>
              <div class="form-field">
                <label>货币2金额</label>
                <input v-model.number="spotForm.ccy2_amount" type="number" step="1" placeholder="如 -33906500" />
              </div>
              <div class="form-field">
                <label>交易日</label>
                <input v-model="spotForm.trade_date" type="date" />
              </div>
              <div class="form-field">
                <label>起息日</label>
                <input v-model="spotForm.value_date" type="date" />
              </div>
              <div class="form-field">
                <label>对手方</label>
                <input v-model="spotForm.counterparty_name" placeholder="对手方名称" />
              </div>
              <div class="form-field">
                <label>投组</label>
                <PortfolioAutocomplete
                  :model-value="spotForm.portfolio_name ?? ''"
                  placeholder="搜索并选择投组..."
                  @update:model-value="(v: string | null) => spotForm.portfolio_name = v"
                  @update:portfolio-id="(v: number | null) => spotFormPortfolioId = v"
                />
              </div>
              <div class="form-field">
                <label>交割状态</label>
                <select v-model="spotForm.delivery_status">
                  <option value="未交割">未交割</option>
                  <option value="已交割">已交割</option>
                </select>
              </div>
              <div class="form-field">
                <label>来源</label>
                <input v-model="spotForm.source" placeholder="如 CSTP下载交易" />
              </div>
              <div class="form-field">
                <label>交易场所</label>
                <input v-model="spotForm.venue" placeholder="如 CFETS" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showSpotModal = false">取消</button>
            <button class="btn-primary" :disabled="spotFormLoading" @click="submitSpotForm">
              {{ spotFormLoading ? '提交中...' : '确认' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ==================== Batch Delete Confirmation ==================== -->
    <Teleport to="body">
      <div v-if="showBatchDeleteConfirm" class="modal-overlay" @click.self="cancelBatchDelete">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3>确认批量删除</h3>
            <button class="modal-close" @click="cancelBatchDelete">&times;</button>
          </div>
          <div class="modal-body">
            <p>确定要删除选中的 <strong>{{ selectedIds.length }}</strong> 条交易吗？此操作不可撤销。</p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="cancelBatchDelete">取消</button>
            <button class="btn-danger" @click="doBatchDelete">删除</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ==================== Spot Batch Delete Confirmation ==================== -->
    <Teleport to="body">
      <div v-if="showSpotBatchDeleteConfirm" class="modal-overlay" @click.self="cancelSpotBatchDelete">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3>确认批量删除</h3>
            <button class="modal-close" @click="cancelSpotBatchDelete">&times;</button>
          </div>
          <div class="modal-body">
            <p>确定要删除选中的 <strong>{{ spotSelectedIds.length }}</strong> 条即期流水吗？此操作不可撤销。</p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="cancelSpotBatchDelete">取消</button>
            <button class="btn-danger" @click="doSpotBatchDelete">删除</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 1.25rem; }

/* Section divider for spot trades in list tab */
.section-divider {
  margin: 1.5rem 0 1rem;
  padding-top: 1rem;
  border-top: 2px solid var(--color-border);
}
.section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

/* Import type selector */
.import-type-selector {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.radio-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--color-text);
}
.radio-label input[type="radio"] {
  accent-color: var(--color-primary);
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  margin-bottom: 1.25rem;
  border-bottom: 2px solid var(--color-border);
}
.tab {
  padding: 0.6rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.tab:hover { color: var(--color-text); }
.tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

/* Toolbar */
.toolbar { display: flex; gap: 1rem; margin-bottom: 1.25rem; align-items: center; }
.toolbar-spacer { flex: 1; }
.filter-group { display: flex; gap: 0.5rem; }
.filter-group select {
  padding: 0.45rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
  cursor: pointer;
}
.filter-group select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-primary:hover { filter: brightness(1.1); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary {
  padding: 0.5rem 1rem;
  background: var(--color-bg-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-secondary:hover { border-color: var(--color-primary); color: var(--color-primary); }
.btn-danger {
  padding: 0.5rem 1rem;
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-danger:hover { filter: brightness(1.1); }

/* Badges */
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

/* Action buttons */
.action-btns { display: flex; gap: 0.35rem; }
.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg-surface);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.action-btn:hover { box-shadow: var(--shadow-sm); }
.action-edit:hover { border-color: var(--color-primary); color: var(--color-primary); }
.action-delete:hover { border-color: #ef4444; color: #ef4444; }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.25rem;
  font-size: 0.8125rem;
}
.page-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg-surface);
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--color-text);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}
.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
}
.page-btn:disabled { opacity: 0.4; cursor: default; }
.page-info { color: var(--color-text-secondary); }
.page-info strong { color: var(--color-primary); }
.page-total { color: var(--color-text-secondary); }

/* Card */
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 0.9375rem; margin-bottom: 0.85rem; }
.card-subtitle { font-size: 0.75rem; color: var(--color-text-secondary); margin-top: -0.5rem; margin-bottom: 0.75rem; }

/* Import */
.file-input-row { display: flex; gap: 1rem; align-items: center; }
.file-input-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.85rem;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
  color: var(--color-text-secondary);
}
.file-input-wrapper:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}
.file-hidden {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.file-text { font-size: 0.875rem; }
.file-info { margin-top: 0.5rem; font-size: 0.8125rem; color: var(--color-primary); font-weight: 500; }
.preview-stats {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 0.85rem;
}
.preview-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 1.25rem;
  border-radius: var(--radius);
  background: var(--color-bg-secondary);
}
.preview-stat-value { font-size: 1.25rem; font-weight: 700; }
.preview-stat-label { font-size: 0.7rem; color: var(--color-text-secondary); margin-top: 0.15rem; }
.preview-stat--success { background: var(--color-positive-bg); }
.preview-stat--success .preview-stat-value { color: var(--color-positive); }
.preview-stat--warning { background: var(--color-warning-bg); }
.preview-stat--warning .preview-stat-value { color: var(--color-warning); }
.preview-stat--error { background: var(--color-negative-bg); }
.preview-stat--error .preview-stat-value { color: var(--color-negative); }
.error-list { margin-top: 0.85rem; font-size: 0.8125rem; }
.error-list h4 { margin-bottom: 0.5rem; color: var(--color-text-secondary); font-size: 0.8125rem; }
.error-item { display: flex; gap: 0.75rem; padding: 0.25rem 0; }
.err-row { color: var(--color-text-secondary); min-width: 2.5rem; }
.err-field { font-family: "SF Mono", "Cascadia Code", "Consolas", monospace; color: var(--color-primary); min-width: 8rem; font-size: 0.75rem; }
.err-msg { color: var(--color-negative); }

/* Mapping */
.mapping-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.4rem;
  font-size: 0.75rem;
}
.mapping-item { display: flex; gap: 0.35rem; align-items: center; padding: 0.25rem 0.5rem; border-radius: var(--radius-sm); transition: background var(--transition-fast); }
.mapping-item:hover { background: var(--color-bg-secondary); }
.csv-header { color: var(--color-text-secondary); }
.arrow { color: var(--color-primary); display: flex; align-items: center; }
.db-field { font-family: "SF Mono", "Cascadia Code", "Consolas", monospace; color: var(--color-text); }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  width: 640px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}
.modal-sm { width: 400px; }
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
}
.modal-header h3 { font-size: 0.9375rem; margin: 0; }
.modal-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.modal-close:hover { color: var(--color-text); }
.modal-body { padding: 1.25rem; }
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--color-border);
}

/* Form */
.form-error {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  margin-bottom: 1rem;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}
.form-field { display: flex; flex-direction: column; gap: 0.3rem; }
.form-field--full { grid-column: 1 / -1; }
.form-field label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}
.form-field .required { color: #ef4444; }
.form-field input,
.form-field select {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.form-field input:focus,
.form-field select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}
.form-field input:disabled {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  cursor: not-allowed;
}
</style>
