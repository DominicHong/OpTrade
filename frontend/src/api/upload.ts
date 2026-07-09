import apiClient from './client'

/** Upload a file via multipart/form-data POST with an extended timeout.
 *
 * Generic ``T`` is the expected response type (defaults to ``unknown``).
 */
export async function uploadFile<T = unknown>(
  url: string,
  file: File,
  timeout = 60000,
): Promise<T> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<T>(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout,
  })
  return data
}
