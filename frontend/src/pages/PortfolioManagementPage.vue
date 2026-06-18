<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useUiStore } from '@/stores/uiStore'
import DataTable from '@/components/shared/DataTable.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import type { TableColumn } from '@/components/shared/DataTable.vue'
import type { Portfolio } from '@/types/portfolio'
import { useModalGuard } from '@/composables/useModalGuard'

const store = usePortfolioStore()
const ui = useUiStore()

// --- Form modal ---
const showModal = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const formError = ref<string | null>(null)
const formLoading = ref(false)

const emptyForm = { name: '', description: '' }
const form = ref({ ...emptyForm })
const editingId = ref<number | null>(null)

// --- Delete confirmation ---
const showDeleteConfirm = ref(false)
const deletingPortfolio = ref<Portfolio | null>(null)

const columns = computed<TableColumn[]>(() => [
  { key: 'actions', label: '操作', width: '120px' },
  { key: 'id', label: 'ID', sortable: true, width: '60px' },
  { key: 'name', label: '投组名称', sortable: true },
  { key: 'description', label: '描述' },
  { key: 'trade_count', label: '交易数量', sortable: true, width: '100px', align: 'right' },
])

onMounted(() => {
  store.loadPortfolios()
})

function openCreateModal() {
  modalMode.value = 'create'
  form.value = { ...emptyForm }
  editingId.value = null
  formError.value = null
  showModal.value = true
}

function openEditModal(p: Portfolio) {
  modalMode.value = 'edit'
  editingId.value = p.id
  form.value = { name: p.name, description: p.description || '' }
  formError.value = null
  showModal.value = true
}

async function submitForm() {
  formLoading.value = true
  formError.value = null
  try {
    if (modalMode.value === 'create') {
      await store.addPortfolio(form.value.name, form.value.description || undefined)
      ui.addNotification('success', '投组创建成功')
    } else if (editingId.value) {
      await store.savePortfolio(editingId.value, {
        name: form.value.name,
        description: form.value.description || null,
      })
      ui.addNotification('success', '投组更新成功')
    }
    showModal.value = false
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    formLoading.value = false
  }
}

function confirmDelete(p: Portfolio) {
  deletingPortfolio.value = p
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deletingPortfolio.value) return
  try {
    await store.removePortfolio(deletingPortfolio.value.id)
    ui.addNotification('success', `投组 "${deletingPortfolio.value.name}" 已删除`)
  } catch (e: unknown) {
    ui.addNotification('error', e instanceof Error ? e.message : '删除失败')
  } finally {
    showDeleteConfirm.value = false
    deletingPortfolio.value = null
  }
}

function cancelDelete() {
  showDeleteConfirm.value = false
  deletingPortfolio.value = null
}

const { onOverlayMousedown, onOverlayClick } = useModalGuard(showModal)
</script>

<template>
  <div class="portfolio-mgmt-page">
    <div class="page-header">
      <h1>投组管理</h1>
      <button class="btn-primary" @click="openCreateModal">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
        新建投组
      </button>
    </div>

    <DataTable
      :columns="columns"
      :rows="store.portfolios as unknown as Record<string, unknown>[]"
      :loading="store.loading"
      sort-by="id"
      sort-order="asc"
      row-key="id"
    >
      <template #cell-actions="{ row }">
        <div class="action-btns" @click.stop>
          <button class="action-btn action-edit" title="编辑" @click="openEditModal(row as unknown as Portfolio)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="action-btn action-delete" title="删除" @click="confirmDelete(row as unknown as Portfolio)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          </button>
        </div>
      </template>
    </DataTable>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @mousedown="onOverlayMousedown" @click="onOverlayClick">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ modalMode === 'create' ? '新建投组' : '编辑投组' }}</h3>
            <button class="modal-close" @click="showModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="formError" class="form-error">{{ formError }}</div>
            <div class="form-grid">
              <div class="form-field form-field--full">
                <label>投组名称 <span class="required">*</span></label>
                <input v-model="form.name" placeholder="输入投组名称" />
              </div>
              <div class="form-field form-field--full">
                <label>描述</label>
                <input v-model="form.description" placeholder="可选描述" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showModal = false">取消</button>
            <button class="btn-primary" :disabled="formLoading || !form.name.trim()" @click="submitForm">
              {{ formLoading ? '提交中...' : '确认' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="cancelDelete">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3>确认删除</h3>
            <button class="modal-close" @click="cancelDelete">&times;</button>
          </div>
          <div class="modal-body">
            <p>确定要删除投组 <strong>"{{ deletingPortfolio?.name }}"</strong> 吗？</p>
            <p v-if="deletingPortfolio?.trade_count" class="delete-warning">
              该投组下有 {{ deletingPortfolio.trade_count }} 条交易，无法删除。请先重新分配或删除关联的交易。
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="cancelDelete">取消</button>
            <button
              class="btn-danger"
              :disabled="!!deletingPortfolio?.trade_count"
              @click="doDelete"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}
.page-header h1 { margin: 0; }

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
.btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }

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
  width: 480px;
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

.form-error {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  margin-bottom: 1rem;
}
.form-grid { display: flex; flex-direction: column; gap: 0.85rem; }
.form-field { display: flex; flex-direction: column; gap: 0.3rem; }
.form-field--full { grid-column: 1 / -1; }
.form-field label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}
.form-field .required { color: #ef4444; }
.form-field input {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.8125rem;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition-fast);
}
.form-field input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}

.delete-warning {
  color: #ef4444;
  font-size: 0.8125rem;
  margin-top: 0.5rem;
}
</style>
