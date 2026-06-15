import { type Ref } from 'vue'

/**
 * Prevents modal overlay from closing when the user starts a drag-selection
 * inside the modal and releases the mouse outside the modal content (on the
 * overlay itself).  Without this guard a simple `@click.self` would see the
 * overlay as the click target and close the dialog.
 *
 * Usage:
 * ```ts
 * const showModal = ref(false)
 * const { onOverlayMousedown, onOverlayClick } = useModalGuard(showModal)
 * ```
 *
 * Template:
 * ```html
 * <div v-if="showModal" class="modal-overlay"
 *      @mousedown="onOverlayMousedown"
 *      @click="onOverlayClick">
 *   <div class="modal">...</div>
 * </div>
 * ```
 */
export function useModalGuard(visible: Ref<boolean>) {
  let overlayMouseDownTarget: EventTarget | null = null

  function onOverlayMousedown(e: MouseEvent) {
    overlayMouseDownTarget = e.target
  }

  function onOverlayClick(e: MouseEvent) {
    // Only close when BOTH mousedown and click originated on the overlay itself
    if (e.target === e.currentTarget && overlayMouseDownTarget === e.currentTarget) {
      visible.value = false
    }
    overlayMouseDownTarget = null
  }

  return { onOverlayMousedown, onOverlayClick }
}
