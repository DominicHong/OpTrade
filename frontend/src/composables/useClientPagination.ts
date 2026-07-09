import { computed, ref } from 'vue'

/** Client-side pagination composable for a reactive array of items.
 *
 * Returns ``page``, ``pageSize``, ``totalPages`` and ``pagedItems`` (the
 * slice of items on the current page).  Mirrors the inline ``ref`` +
 * ``computed`` pattern that was duplicated across the detail tables.
 */
export function useClientPagination<T>(items: () => T[], pageSize = 10) {
  const page = ref(1)
  const totalPages = computed(() =>
    Math.max(1, Math.ceil(items().length / pageSize)),
  )
  const pagedItems = computed(() => {
    const start = (page.value - 1) * pageSize
    return items().slice(start, start + pageSize)
  })
  return { page, pageSize, totalPages, pagedItems }
}
