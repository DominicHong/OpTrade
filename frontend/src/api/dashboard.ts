import apiClient from './client'
import type {
  DashboardSummary,
  DashboardAnalysisRequest,
  DashboardDefaultsResponse,
} from '@/types/api'
import type { AggregatedAnalysisResponse } from '@/types/portfolio'

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await apiClient.get('/dashboard/summary')
  return data
}

export async function fetchDashboardAnalysis(
  params: DashboardAnalysisRequest,
): Promise<AggregatedAnalysisResponse> {
  const { data } = await apiClient.post('/dashboard/analysis', params)
  return data
}

export async function fetchDashboardDefaults(): Promise<DashboardDefaultsResponse> {
  const { data } = await apiClient.get('/dashboard/defaults')
  return data
}
