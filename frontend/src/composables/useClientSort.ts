import { computed, ref } from 'vue'

export type SortOrder = 'asc' | 'desc'

export interface SortColumn {
  key: string
  label: string
  sortable?: boolean
  type?: 'string' | 'number' | 'date'
  align?: 'left' | 'right' | 'center'
}

export interface UseClientSortOptions<T extends object> {
  items: () => T[]
  defaultSortBy: string
  defaultSortOrder?: SortOrder
  getColumnType?: (key: string) => 'string' | 'number' | 'date' | undefined
}

function compareValues(
  a: unknown,
  b: unknown,
  type?: 'string' | 'number' | 'date',
): number {
  const nullableA = a == null
  const nullableB = b == null
  if (nullableA && nullableB) return 0
  if (nullableA) return 1
  if (nullableB) return -1

  if (type === 'number') {
    const na = Number(a)
    const nb = Number(b)
    if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb
  }

  if (type === 'date') {
    const da = typeof a === 'string' ? new Date(a) : new Date(Number(a))
    const db = typeof b === 'string' ? new Date(b) : new Date(Number(b))
    if (!Number.isNaN(da.getTime()) && !Number.isNaN(db.getTime())) {
      return da.getTime() - db.getTime()
    }
  }

  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

export function useClientSort<T extends object>(
  options: UseClientSortOptions<T>,
) {
  const sortBy = ref<string>(options.defaultSortBy)
  const sortOrder = ref<SortOrder>(options.defaultSortOrder ?? 'asc')

  function toggleSort(key: string) {
    if (sortBy.value === key) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy.value = key
      sortOrder.value = 'asc'
    }
  }

  function setSort(key: string, order: SortOrder = 'asc') {
    sortBy.value = key
    sortOrder.value = order
  }

  const sortedItems = computed(() => {
    const key = sortBy.value
    const order = sortOrder.value
    const type = options.getColumnType?.(key)
    const list = [...options.items()]
    if (!key) return list

    return list.sort((a, b) => {
      const rowA = a as Record<string, unknown>
      const rowB = b as Record<string, unknown>
      const cmp = compareValues(rowA[key], rowB[key], type)
      return order === 'asc' ? cmp : -cmp
    })
  })

  return {
    sortBy,
    sortOrder,
    sortedItems,
    toggleSort,
    setSort,
  }
}
