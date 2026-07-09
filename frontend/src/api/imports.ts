import apiClient from './client'
import type { ImportConfirmResponse, ImportHistoryItem } from '@/types/api'
import { uploadFile as postFile } from './upload'

export async function uploadFile(file: File): Promise<ImportConfirmResponse> {
  return postFile<ImportConfirmResponse>('/imports/upload', file)
}

export async function getImportHistory(): Promise<ImportHistoryItem[]> {
  const { data } = await apiClient.get('/imports/history')
  return data
}

export async function getColumnMapping(): Promise<{ mapping: Record<string, string>; total_columns: number }> {
  const { data } = await apiClient.get('/imports/columns')
  return data
}
