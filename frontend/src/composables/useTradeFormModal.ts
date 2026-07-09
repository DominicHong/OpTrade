import { ref } from 'vue'
import type { Ref } from 'vue'

/** State + actions shared by the option/spot/swap create-edit form modals.
 *
 * The three trade types had identical modal-state bookkeeping (showModal,
 * modalMode, formError, formLoading, editingId, formPortfolioId) and
 * near-identical submit/delete handlers that differed only in the store,
 * the payload transform and the notification message.  This composable
 * encapsulates the common state; callers pass hooks for the differences.
 */
export function useTradeFormModal<F>(emptyForm: F) {
  const showModal = ref(false)
  const modalMode = ref<'create' | 'edit'>('create')
  const formError = ref<string | null>(null)
  const formLoading = ref(false)
  const editingId = ref<number | null>(null)
  const formPortfolioId = ref<number | null>(null)
  const form = ref({ ...emptyForm }) as Ref<F>

  function openCreate() {
    modalMode.value = 'create'
    form.value = { ...emptyForm }
    editingId.value = null
    formPortfolioId.value = null
    formError.value = null
    showModal.value = true
  }

  function openEdit(id: number, portfolioId: number | null, fields: Partial<F>) {
    modalMode.value = 'edit'
    editingId.value = id
    formPortfolioId.value = portfolioId
    form.value = { ...emptyForm, ...fields } as F
    formError.value = null
    showModal.value = true
  }

  /** Submit the form.  *store* must expose addTrade/saveTrade/loadTrades.
   *  *transformPayload* runs on the form before sending (e.g. volatility /100).
   *  Returns true on success so the caller can close the modal. */
  async function submit(
    store: {
      addTrade(payload: F): Promise<unknown>
      saveTrade(id: number, payload: F): Promise<unknown>
      loadTrades(): Promise<unknown>
    },
    transformPayload: (form: F) => F,
    notify: (type: 'success' | 'error', msg: string) => void,
    msgs: { create: string; update: string; fail: string },
  ): Promise<boolean> {
    formLoading.value = true
    formError.value = null
    const payload = transformPayload({ ...form.value, portfolio_id: formPortfolioId.value } as F)
    try {
      if (modalMode.value === 'create') {
        await store.addTrade(payload)
        notify('success', msgs.create)
      } else if (editingId.value) {
        await store.saveTrade(editingId.value, payload)
        notify('success', msgs.update)
      }
      showModal.value = false
      store.loadTrades()
      return true
    } catch (e: unknown) {
      formError.value = e instanceof Error ? e.message : msgs.fail
      return false
    } finally {
      formLoading.value = false
    }
  }

  return {
    showModal, modalMode, formError, formLoading, editingId, formPortfolioId, form,
    openCreate, openEdit, submit,
  }
}
