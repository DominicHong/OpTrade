import apiClient from './client'

/** Minimal shape of a paginated list response. */
export interface ListResponse<T> {
  data: T[]
  total: number
  page: number
  page_size: number
}

/** Build the six standard CRUD API functions for a trade resource.
 *
 * *resource* is the URL prefix including the leading slash, e.g.
 * ``'/option-trades'``.  The returned object has ``fetchList``, ``fetchOne``,
 * ``create``, ``update``, ``remove`` and ``batchDelete``.
 */
export function createCrudApi<T, C, U, F, R extends ListResponse<T>>(resource: string) {
  return {
    fetchList: async (params: F = {} as F): Promise<R> => {
      const { data } = await apiClient.get<R>(resource, { params })
      return data
    },
    fetchOne: async (id: number): Promise<T> => {
      const { data } = await apiClient.get<T>(`${resource}/${id}`)
      return data
    },
    create: async (payload: C): Promise<T> => {
      const { data } = await apiClient.post<T>(resource, payload)
      return data
    },
    update: async (id: number, payload: U): Promise<T> => {
      const { data } = await apiClient.put<T>(`${resource}/${id}`, payload)
      return data
    },
    remove: async (id: number): Promise<void> => {
      await apiClient.delete(`${resource}/${id}`)
    },
    batchDelete: async (ids: number[]): Promise<{ status: string; count: string }> => {
      const { data } = await apiClient.post<{ status: string; count: string }>(
        `${resource}/batch-delete`, { ids },
      )
      return data
    },
  }
}
