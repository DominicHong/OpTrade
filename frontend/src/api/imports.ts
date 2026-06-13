import apiClient from './client'
import type { ImportConfirmResponse, ImportHistoryItem } from '@/types/api'

export async function uploadFile(file: File): Promise<ImportConfirmResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/imports/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

export async function getImportHistory(): Promise<ImportHistoryItem[]> {
  const { data } = await apiClient.get('/imports/history')
  return data
}

export async function getColumnMapping(): Promise<{ mapping: Record<string, string>; total_columns: number }> {
  const { data } = await apiClient.get('/imports/columns')
  return data
}
